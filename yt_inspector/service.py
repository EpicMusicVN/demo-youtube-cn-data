import os

from .analysis import analyze_trends
from .competitor_metrics import compute_competitor_metrics
from .config import load_dotenv, get_int
from .parsers import parse_input_target, parse_keywords
from .video_utils import format_video, reorder_videos, split_long_short, is_short_threshold
from .youtube_api import api_get


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


def fetch_top_viewed_videos(channel_id, max_results=10, video_duration=None, allow_fallback=True):
    base_params = {
        "part": "snippet",
        "type": "video",
        "channelId": channel_id,
        "order": "viewCount",
        "maxResults": max_results,
    }
    if video_duration:
        base_params["videoDuration"] = video_duration

    def run_search(params):
        return api_get("/search", params)

    try:
        data = run_search(base_params)
    except RuntimeError as exc:
        if "invalidFilters" not in str(exc):
            raise
        if not allow_fallback:
            raise
        # Fallback 1: drop videoDuration if present.
        params = dict(base_params)
        params.pop("videoDuration", None)
        try:
            data = run_search(params)
        except RuntimeError as exc2:
            if "invalidFilters" not in str(exc2):
                raise
            # Fallback 2: drop order as well (API sometimes rejects filter combos).
            params.pop("order", None)
            try:
                data = run_search(params)
            except RuntimeError as exc3:
                if "invalidFilters" in str(exc3):
                    return []
                raise
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
    items = []
    chunk_size = 50
    for idx in range(0, len(video_ids), chunk_size):
        chunk = video_ids[idx : idx + chunk_size]
        data = api_get(
            "/videos",
            {
                "part": "snippet,contentDetails,statistics,topicDetails,paidProductPlacementDetails",
                "id": ",".join(chunk),
                "maxResults": len(chunk),
            },
        )
        items.extend(data.get("items", []))
    return items


def channel_id_to_playlist(channel_id, prefix="UU"):
    if not channel_id or not channel_id.startswith("UC"):
        return None
    return prefix + channel_id[2:]


def _build_channel_dict(channel_id, channel):
    """Assemble the public ``channel`` payload shared by both inspect paths."""
    snippet = channel.get("snippet", {})
    branding = channel.get("brandingSettings", {}).get("channel", {})
    stats = channel.get("statistics", {})
    topic = channel.get("topicDetails", {})
    keywords_raw = branding.get("keywords", "")
    return {
        "id": channel_id,
        "name": snippet.get("title"),
        "description": snippet.get("description"),
        "customUrl": snippet.get("customUrl"),
        "publishedAt": snippet.get("publishedAt"),
        "country": snippet.get("country"),
        "keywordsRaw": keywords_raw,
        "keywords": parse_keywords(keywords_raw),
        "topics": topic.get("topicCategories", []),
        "statistics": {
            "viewCount": stats.get("viewCount"),
            "subscriberCount": stats.get("subscriberCount"),
            "videoCount": stats.get("videoCount"),
            "hiddenSubscriberCount": stats.get("hiddenSubscriberCount"),
        },
        "bannerUrl": branding.get("image", {}).get("bannerExternalUrl"),
    }


def inspect_channel(target, enable_analysis=True):
    load_dotenv()
    channel_id = resolve_channel_id(target)
    if not channel_id:
        raise RuntimeError("Could not resolve channel ID from input.")

    channel = fetch_channel_details(channel_id)
    if not channel:
        raise RuntimeError("Channel not found or not accessible.")

    snippet = channel.get("snippet", {})
    content = channel.get("contentDetails", {})
    uploads_playlist_id = content.get("relatedPlaylists", {}).get("uploads")

    fetch_max = get_int("VIDEO_FETCH_MAX", 50)
    if fetch_max > 50:
        fetch_max = 50
    if fetch_max < 10:
        fetch_max = 10
    output_max = get_int("VIDEO_OUTPUT_MAX", 10)
    if output_max < 1:
        output_max = 10

    latest_video_ids = fetch_latest_videos(uploads_playlist_id, max_results=fetch_max) if uploads_playlist_id else []

    use_uush = os.environ.get("USE_UUSH_PLAYLIST", "1") == "1"
    shorts_playlist_id = channel_id_to_playlist(channel_id, prefix="UUSH") if use_uush else None
    shorts_video_ids = []
    if shorts_playlist_id:
        try:
            shorts_video_ids = fetch_latest_videos(shorts_playlist_id, max_results=fetch_max)
        except RuntimeError:
            shorts_video_ids = []

    top_viewed_ids = fetch_top_viewed_videos(channel_id, max_results=fetch_max)
    top_short_from_search = True
    try:
        top_viewed_short_ids = fetch_top_viewed_videos(
            channel_id, max_results=fetch_max, video_duration="short", allow_fallback=False
        )
    except RuntimeError as exc:
        if "invalidFilters" in str(exc):
            top_viewed_short_ids = []
            top_short_from_search = False
        else:
            raise

    latest_videos = fetch_videos_details(latest_video_ids)
    top_union_ids = list(dict.fromkeys(top_viewed_ids + top_viewed_short_ids))
    top_videos = fetch_videos_details(top_union_ids)
    shorts_videos = fetch_videos_details(shorts_video_ids)

    latest_videos_ordered = reorder_videos(latest_video_ids, latest_videos)
    top_videos_ordered = reorder_videos(top_viewed_ids, top_videos)
    top_short_videos_ordered = reorder_videos(top_viewed_short_ids, top_videos)

    latest_formatted = [format_video(v) for v in latest_videos_ordered]
    top_formatted = [format_video(v) for v in top_videos_ordered]
    top_short_formatted = [format_video(v) for v in top_short_videos_ordered]
    shorts_formatted = [format_video(v) for v in reorder_videos(shorts_video_ids, shorts_videos)]

    shorts_id_set = {v.get("id") for v in shorts_formatted if v.get("id")}
    use_uush_for_shorts = use_uush and bool(shorts_id_set)
    if use_uush_for_shorts:
        latest_short = shorts_formatted
        latest_long = [v for v in latest_formatted if v.get("id") not in shorts_id_set]
    else:
        latest_long, latest_short = split_long_short(latest_formatted)

    def unique_by_id(videos):
        seen = set()
        unique = []
        for video in videos:
            vid = video.get("id")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            unique.append(video)
        return unique

    def sort_by_views(videos):
        def to_int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        return sorted(videos, key=lambda v: to_int(v.get("views")), reverse=True)

    if use_uush_for_shorts:
        if top_short_formatted and top_short_from_search:
            top_short_candidates = [v for v in top_short_formatted if v.get("id") in shorts_id_set]
        else:
            top_short_candidates = [v for v in top_formatted if v.get("id") in shorts_id_set]
        if not top_short_candidates:
            top_short_candidates = [v for v in shorts_formatted if v.get("id") in shorts_id_set]
        top_long_candidates = [v for v in top_formatted if v.get("id") not in shorts_id_set]
    else:
        base_short_list = top_short_formatted if (top_short_formatted and top_short_from_search) else top_formatted
        top_short_candidates = [v for v in base_short_list if is_short_threshold(v.get("durationSeconds"))]
        top_long_candidates = [v for v in top_formatted if not is_short_threshold(v.get("durationSeconds"))]

    top_short = sort_by_views(unique_by_id(top_short_candidates))
    top_long = sort_by_views(unique_by_id(top_long_candidates))

    channel_data = _build_channel_dict(channel_id, channel)
    result = {
        "channel": channel_data,
        "topViewed": top_formatted[:output_max],
        "latest": latest_formatted[:output_max],
        "topViewedLong": top_long[:output_max],
        "topViewedShort": top_short[:output_max],
        "latestLong": latest_long[:output_max],
        "latestShort": latest_short[:output_max],
        "competitorAnalysis": compute_competitor_metrics(channel_data, latest_formatted),
    }

    if enable_analysis and os.environ.get("VERTEX_API_KEY"):
        try:
            result["analysis"] = analyze_trends(
                snippet.get("title") or "Channel",
                top_videos,
                latest_videos,
                top_formatted,
                latest_formatted,
            )
        except RuntimeError as exc:
            result["analysis"] = {"enabled": False, "error": str(exc)}

    return result


def inspect_channel_lean(target, enable_analysis=True):
    """Lean inspect powering the hidden /secret competitor page.

    Skips the costly top-viewed ``/search`` calls and the UUSH playlist — only
    channel details + latest uploads are fetched (~11 quota units). Returns the
    channel payload plus the full competitor-analysis block.
    """
    load_dotenv()
    channel_id = resolve_channel_id(target)
    if not channel_id:
        raise RuntimeError("Could not resolve channel ID from input.")

    channel = fetch_channel_details(channel_id)
    if not channel:
        raise RuntimeError("Channel not found or not accessible.")

    content = channel.get("contentDetails", {})
    uploads_playlist_id = content.get("relatedPlaylists", {}).get("uploads")

    fetch_max = get_int("VIDEO_FETCH_MAX", 50)
    if fetch_max > 50:
        fetch_max = 50
    if fetch_max < 10:
        fetch_max = 10

    latest_video_ids = (
        fetch_latest_videos(uploads_playlist_id, max_results=fetch_max)
        if uploads_playlist_id else []
    )
    latest_videos = fetch_videos_details(latest_video_ids)
    latest_formatted = [format_video(v) for v in reorder_videos(latest_video_ids, latest_videos)]

    channel_data = _build_channel_dict(channel_id, channel)
    result = {
        "channel": channel_data,
        "competitorAnalysis": compute_competitor_metrics(channel_data, latest_formatted),
    }

    if enable_analysis and os.environ.get("VERTEX_API_KEY"):
        try:
            # No top-viewed list in lean mode: AI analyses the latest uploads only.
            result["analysis"] = analyze_trends(
                channel_data.get("name") or "Channel",
                [],
                latest_videos,
                [],
                latest_formatted,
            )
        except RuntimeError as exc:
            result["analysis"] = {"enabled": False, "error": str(exc)}

    return result
