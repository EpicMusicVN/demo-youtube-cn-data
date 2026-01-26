#!/usr/bin/env python3
import json
import os
import re
import sys
import shlex
import ssl
import urllib.parse
import urllib.request
import urllib.error

API_BASE = "https://www.googleapis.com/youtube/v3"

# RUN
#

def load_dotenv(path=".env"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                if raw.startswith("export "):
                    raw = raw[len("export "):].strip()
                if "=" not in raw:
                    continue
                key, value = raw.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        return


def api_get(path, params):
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing YOUTUBE_API_KEY env var")
    params = dict(params)
    params["key"] = api_key
    url = API_BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    ssl_no_verify = os.environ.get("YOUTUBE_SSL_NO_VERIFY") == "1"
    context = None
    if ssl_no_verify:
        context = ssl._create_unverified_context()
    else:
        try:
            import certifi  # type: ignore
            context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            context = None
    try:
        with urllib.request.urlopen(req, context=context) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} error: {body}") from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                "SSL verify failed. For shareable runs, install certifi "
                "(pip install certifi) or run macOS 'Install Certificates.command'. "
                "As a last resort for testing only, set YOUTUBE_SSL_NO_VERIFY=1."
            ) from None
        raise RuntimeError(f"URL error: {e}") from None


def parse_duration_iso8601(duration):
    if not duration:
        return None
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not m:
        return None
    h = int(m.group(1) or 0)
    mnt = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mnt * 60 + s


def pick_thumbnail(thumbnails):
    if not thumbnails:
        return None
    for key in ["maxres", "standard", "high", "medium", "default"]:
        if key in thumbnails and "url" in thumbnails[key]:
            return thumbnails[key]["url"]
    return None


def extract_video_id_from_url(u):
    try:
        parsed = urllib.parse.urlparse(u)
    except Exception:
        return None
    qs = urllib.parse.parse_qs(parsed.query)
    if "v" in qs and qs["v"]:
        return qs["v"][0]
    if parsed.netloc in ("youtu.be", "www.youtu.be"):
        vid = parsed.path.strip("/")
        return vid or None
    return None


def parse_input_target(target):
    # Returns dict with possible keys: channel_id, handle, username, custom, video_id
    if not target:
        return {}
    # Normalize whitespace in pasted URLs/handles (newlines, tabs, spaces).
    target = "".join(str(target).split())
    if target.startswith("UC") and len(target) >= 20:
        return {"channel_id": target}
    if target.startswith("@"):
        return {"handle": target[1:]}

    video_id = extract_video_id_from_url(target)
    if video_id:
        return {"video_id": video_id}

    if "://" not in target:
        # treat as handle or custom string
        return {"handle": target}

    try:
        parsed = urllib.parse.urlparse(target)
    except Exception:
        return {"handle": target}

    path = parsed.path.strip("/")
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return {"handle": target}

    for seg in segments:
        if seg.startswith("@"):
            return {"handle": seg[1:]}

    if segments[0] == "channel" and len(segments) >= 2:
        return {"channel_id": segments[1]}
    if segments[0] == "user" and len(segments) >= 2:
        return {"username": segments[1]}
    if segments[0] == "c" and len(segments) >= 2:
        return {"custom": segments[1]}

    # fallback to last segment as handle/custom
    return {"handle": segments[-1]}


def get_channel_by(params):
    data = api_get("/channels", params)
    items = data.get("items", [])
    return items[0] if items else None


def resolve_channel_id(target):
    info = parse_input_target(target)

    if "video_id" in info:
        data = api_get("/videos", {"part": "snippet", "id": info["video_id"]})
        items = data.get("items", [])
        if items:
            return items[0]["snippet"].get("channelId")

    parts = "snippet,contentDetails,brandingSettings,statistics,topicDetails"

    if "channel_id" in info:
        channel = get_channel_by({"part": parts, "id": info["channel_id"]})
        if channel:
            return channel["id"]

    if "handle" in info and info["handle"]:
        try:
            channel = get_channel_by({"part": parts, "forHandle": info["handle"]})
            if channel:
                return channel["id"]
        except RuntimeError:
            # Some API setups may not support forHandle; fall back to search.
            pass

    if "username" in info and info["username"]:
        channel = get_channel_by({"part": parts, "forUsername": info["username"]})
        if channel:
            return channel["id"]

    if "custom" in info and info["custom"]:
        search = api_get(
            "/search",
            {
                "part": "snippet",
                "type": "channel",
                "q": info["custom"],
                "maxResults": 1,
            },
        )
        items = search.get("items", [])
        if items:
            return items[0]["id"].get("channelId")

    # fallback: try search by query
    if "handle" in info and info["handle"]:
        search = api_get(
            "/search",
            {
                "part": "snippet",
                "type": "channel",
                "q": info["handle"],
                "maxResults": 1,
            },
        )
        items = search.get("items", [])
        if items:
            return items[0]["id"].get("channelId")

    return None


def parse_keywords(raw):
    if not raw:
        return []
    try:
        return shlex.split(raw)
    except Exception:
        return raw.split()


def fetch_channel_details(channel_id):
    parts = "snippet,contentDetails,brandingSettings,statistics,topicDetails"
    channel = get_channel_by({"part": parts, "id": channel_id})
    return channel


def fetch_latest_videos(uploads_playlist_id, max_results=10):
    data = api_get(
        "/playlistItems",
        {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": max_results,
        },
    )
    items = data.get("items", [])
    video_ids = [item["contentDetails"]["videoId"] for item in items if "contentDetails" in item]
    return video_ids


def fetch_top_viewed_videos(channel_id, max_results=10):
    data = api_get(
        "/search",
        {
            "part": "snippet",
            "type": "video",
            "channelId": channel_id,
            "order": "viewCount",
            "maxResults": max_results,
        },
    )
    items = data.get("items", [])
    video_ids = []
    for item in items:
        vid = item.get("id", {}).get("videoId")
        if vid:
            video_ids.append(vid)
    return video_ids


def fetch_videos_details(video_ids):
    if not video_ids:
        return []
    data = api_get(
        "/videos",
        {
            "part": "snippet,contentDetails,statistics,topicDetails",
            "id": ",".join(video_ids),
            "maxResults": len(video_ids),
        },
    )
    return data.get("items", [])


def format_video(item):
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})
    topic = item.get("topicDetails", {})

    duration_iso = content.get("duration")
    duration_seconds = parse_duration_iso8601(duration_iso)

    return {
        "id": item.get("id"),
        "title": snippet.get("title"),
        "url": f"https://www.youtube.com/watch?v={item.get('id')}",
        "publishedAt": snippet.get("publishedAt"),
        "views": stats.get("viewCount"),
        "likes": stats.get("likeCount"),
        "comments": stats.get("commentCount"),
        "duration": duration_iso,
        "durationSeconds": duration_seconds,
        "tags": snippet.get("tags", []),
        "thumbnail": pick_thumbnail(snippet.get("thumbnails")),
        "description": snippet.get("description"),
        "channelId": snippet.get("channelId"),
        "channelTitle": snippet.get("channelTitle"),
        "topics": topic.get("topicCategories", []),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: yt_channel_inspector.py <channel_url_or_id_or_handle>")
        sys.exit(1)

    target = " ".join(sys.argv[1:])
    channel_id = resolve_channel_id(target)
    if not channel_id:
        print("Could not resolve channel ID from input.")
        sys.exit(2)

    channel = fetch_channel_details(channel_id)
    if not channel:
        print("Channel not found or not accessible.")
        sys.exit(3)

    snippet = channel.get("snippet", {})
    branding = channel.get("brandingSettings", {}).get("channel", {})
    stats = channel.get("statistics", {})
    topic = channel.get("topicDetails", {})
    content = channel.get("contentDetails", {})

    uploads_playlist_id = content.get("relatedPlaylists", {}).get("uploads")

    keywords_raw = branding.get("keywords", "")
    keywords = parse_keywords(keywords_raw)

    latest_video_ids = fetch_latest_videos(uploads_playlist_id, max_results=10) if uploads_playlist_id else []
    top_viewed_ids = fetch_top_viewed_videos(channel_id, max_results=10)

    latest_videos = fetch_videos_details(latest_video_ids)
    top_videos = fetch_videos_details(top_viewed_ids)

    result = {
        "channel": {
            "id": channel_id,
            "name": snippet.get("title"),
            "description": snippet.get("description"),
            "customUrl": snippet.get("customUrl"),
            "publishedAt": snippet.get("publishedAt"),
            "country": snippet.get("country"),
            "keywordsRaw": keywords_raw,
            "keywords": keywords,
            "topics": topic.get("topicCategories", []),
            "statistics": {
                "viewCount": stats.get("viewCount"),
                "subscriberCount": stats.get("subscriberCount"),
                "videoCount": stats.get("videoCount"),
                "hiddenSubscriberCount": stats.get("hiddenSubscriberCount"),
            },
            "bannerUrl": branding.get("image", {}).get("bannerExternalUrl"),
        },
        "topViewed": [format_video(v) for v in top_videos],
        "latest": [format_video(v) for v in latest_videos],
    }

    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)
