import os
import time
import json

from .config import get_float, get_int
from .openrouter import openrouter_generate
from .video_utils import pick_thumbnail_for_analysis


def build_trends_prompt(channel_name, top_videos, latest_videos):
    def lines_from(videos):
        lines = []
        for idx, video in enumerate(videos, 1):
            title = video.get("title") or "Untitled"
            views = video.get("views") or "0"
            published = video.get("publishedAt") or "unknown date"
            lines.append(f"{idx}. {title} | {views} views | {published}")
        return "\n".join(lines)

    return (
        "You are a YouTube strategist. Analyze patterns in titles and thumbnails.\n"
        "Return ONLY valid JSON with keys:\n"
        "- titleTrends (array of 3-6 bullet strings)\n"
        "- thumbnailTrends (array of 3-6 bullet strings)\n"
        "- titleFormula (string)\n"
        "- thumbnailFormula (string)\n"
        "- caveats (string, optional)\n\n"
        f"Channel: {channel_name}\n\n"
        "Top viewed videos:\n"
        f"{lines_from(top_videos)}\n\n"
        "Latest videos:\n"
        f"{lines_from(latest_videos)}\n\n"
        "Thumbnails are attached as images when available. If thumbnails are missing, "
        "focus on title patterns and note that thumbnail analysis is limited in caveats."
    )


def parse_json_from_text(text):
    if not text:
        return None
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        # Prefer fenced block content if present.
        if len(parts) >= 3:
            text = parts[1]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].strip()
        else:
            text = text.replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


def collect_thumbnail_samples(videos, label_prefix, max_items=5, deadline=None):
    samples = []
    seen = set()
    for idx, item in enumerate(videos, 1):
        if deadline and time.monotonic() > deadline:
            break
        if len(samples) >= max_items:
            break
        snippet = item.get("snippet", {})
        thumbs = snippet.get("thumbnails", {})
        url = pick_thumbnail_for_analysis(thumbs)
        if not url or url in seen:
            continue
        seen.add(url)
        title = snippet.get("title") or f"{label_prefix} {idx}"
        label = f"{label_prefix} thumbnail for: {title}"
        samples.append((label, url))
    return samples


def analyze_trends(channel_name, top_videos_raw, latest_videos_raw, top_videos_fmt, latest_videos_fmt):
    budget = get_float(
        "ANALYSIS_BUDGET_SECONDS",
        get_float("OPENROUTER_BUDGET_SECONDS", get_float("GEMINI_BUDGET_SECONDS", 20)),
    )
    deadline = time.monotonic() + max(budget, 5.0)

    prompt = build_trends_prompt(channel_name, top_videos_fmt, latest_videos_fmt)

    max_thumbs = get_int(
        "ANALYSIS_THUMBNAILS_MAX",
        get_int("OPENROUTER_THUMBNAILS_MAX", get_int("GEMINI_THUMBNAILS_MAX", 6)),
    )
    half = max(1, max_thumbs // 2)

    image_items = []
    image_items.extend(collect_thumbnail_samples(top_videos_raw, "Top", max_items=half, deadline=deadline))
    image_items.extend(
        collect_thumbnail_samples(latest_videos_raw, "Latest", max_items=max_thumbs - half, deadline=deadline)
    )

    if time.monotonic() > deadline:
        return {"enabled": False, "reason": "Analysis timed out before OpenRouter call."}

    response_text = openrouter_generate(prompt, image_items=image_items)
    if not response_text:
        return {"enabled": False, "reason": "OpenRouter did not return a response."}

    parsed = parse_json_from_text(response_text)
    if not parsed:
        return {"enabled": True, "raw": response_text}

    def normalize_list(value, max_items=6):
        if not value:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.splitlines() if item.strip()]
        else:
            items = [str(item).strip() for item in value if str(item).strip()]
        seen = set()
        unique = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
            if len(unique) >= max_items:
                break
        return unique

    parsed["titleTrends"] = normalize_list(parsed.get("titleTrends"))
    parsed["thumbnailTrends"] = normalize_list(parsed.get("thumbnailTrends"))
    parsed["enabled"] = True
    return parsed
