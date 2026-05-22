"""Fetch YouTube video comments for user / AI analysis.

Uses the public ``commentThreads.list`` endpoint — 1 quota unit per page of up
to 100 comments. Top-level comments are returned together with their inline
replies (the API includes up to ~5 replies per thread).
"""
import re

from .config import load_dotenv
from .parsers import extract_video_id_from_url
from .youtube_api import api_get

# A YouTube video ID is always 11 chars from this alphabet.
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
# Matches IDs inside /shorts/, /live/ and /embed/ style URLs.
_PATH_ID_RE = re.compile(r"/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})")

# Hard cap on comments per request — keeps quota predictable (1 unit / 100).
MAX_COMMENTS = 500


def resolve_video_id(target):
    """Extract an 11-char video ID from a URL, /shorts/ link, or bare ID."""
    target = (target or "").strip()
    if not target:
        return None
    if _VIDEO_ID_RE.match(target):
        return target
    vid = extract_video_id_from_url(target)
    if vid and _VIDEO_ID_RE.match(vid):
        return vid
    match = _PATH_ID_RE.search(target)
    if match:
        return match.group(1)
    return None


def _format_comment(snippet):
    """Reduce a raw comment snippet to the fields the UI / analysis need."""
    return {
        "author": snippet.get("authorDisplayName"),
        "text": snippet.get("textOriginal") or snippet.get("textDisplay") or "",
        "likes": snippet.get("likeCount", 0) or 0,
        "publishedAt": snippet.get("publishedAt"),
    }


def _friendly_error(message):
    """Map raw YouTube API errors to readable, user-facing messages.

    Fails closed: unrecognised errors return a generic message so the raw
    Google API error body (quota state, project details) is never leaked to
    the client. The raw message is still logged server-side by the caller.
    """
    if "commentsDisabled" in message:
        return "Comments are disabled for this video."
    if "videoNotFound" in message:
        return "Video not found — check the URL."
    if "quotaExceeded" in message:
        return "YouTube API quota exceeded — try again later."
    if "HTTP 403" in message:
        return "Cannot access comments for this video (private or restricted)."
    return "Could not fetch comments. Please try again later."


def fetch_comments(target, max_results=100, order="relevance"):
    """Fetch up to ``max_results`` top-level comments (with inline replies).

    Returns ``{"videoId", "count", "comments": [...]}`` where each comment has
    ``author``, ``text``, ``likes``, ``publishedAt``, ``replyCount`` and a
    ``replies`` list of the same comment shape.
    """
    load_dotenv()
    video_id = resolve_video_id(target)
    if not video_id:
        raise RuntimeError("Could not extract a video ID from the input.")

    try:
        max_results = int(max_results)
    except (TypeError, ValueError):
        max_results = 100
    max_results = max(1, min(max_results, MAX_COMMENTS))
    order = order if order in ("relevance", "time") else "relevance"

    comments = []
    page_token = None
    pages = 0
    # Page cap guards against quota waste if the API keeps returning a
    # nextPageToken with empty/filtered item lists (heavily moderated videos).
    max_pages = (max_results + 99) // 100 + 2
    while len(comments) < max_results and pages < max_pages:
        pages += 1
        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": min(100, max_results - len(comments)),
            "order": order,
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            data = api_get("/commentThreads", params)
        except RuntimeError as exc:
            print(f"WARNING: commentThreads fetch failed — {exc}")
            raise RuntimeError(_friendly_error(str(exc))) from None

        for item in data.get("items", []):
            thread = item.get("snippet", {})
            top = thread.get("topLevelComment", {}).get("snippet", {})
            entry = _format_comment(top)
            # Skip ghost entries left behind by deleted / empty comments.
            if not entry["author"] and not entry["text"].strip():
                continue
            entry["replyCount"] = thread.get("totalReplyCount", 0) or 0
            entry["replies"] = [
                _format_comment(reply.get("snippet", {}))
                for reply in item.get("replies", {}).get("comments", [])
            ]
            comments.append(entry)
            if len(comments) >= max_results:
                break

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    # truncated = more comments likely exist beyond what was returned.
    truncated = len(comments) >= max_results or bool(page_token)
    return {
        "videoId": video_id,
        "count": len(comments),
        "comments": comments,
        "truncated": truncated,
    }
