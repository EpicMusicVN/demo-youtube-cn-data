import os

from .config import get_int
from .parsers import parse_duration_iso8601


def pick_thumbnail(thumbnails):
    if not thumbnails:
        return None
    for key in ["maxres", "standard", "high", "medium", "default"]:
        if key in thumbnails and "url" in thumbnails[key]:
            return thumbnails[key]["url"]
    return None


def pick_thumbnail_for_analysis(thumbnails):
    if not thumbnails:
        return None
    for key in ["high", "medium", "standard", "default", "maxres"]:
        if key in thumbnails and "url" in thumbnails[key]:
            return thumbnails[key]["url"]
    return None


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


def reorder_videos(video_ids, items):
    lookup = {item.get("id"): item for item in items}
    ordered = []
    for vid in video_ids:
        if vid in lookup:
            ordered.append(lookup[vid])
    return ordered


def split_long_short(videos):
    short_max = get_int("SHORT_MAX_SECONDS", 240)
    if short_max < 1:
        short_max = 240
    shorts = []
    longs = []
    for video in videos:
        seconds = video.get("durationSeconds")
        if seconds is not None and seconds < short_max:
            shorts.append(video)
        else:
            longs.append(video)
    return longs, shorts


def is_short_threshold(seconds):
    short_max = get_int("SHORT_MAX_SECONDS", 240)
    if short_max < 1:
        short_max = 240
    return seconds is not None and seconds < short_max
