import json
import os
import time

from .analysis_prompt import build_trends_prompt, summarize_metrics
from .config import get_float, get_int
from .media import fetch_url_bytes
from .vertex_ai import vertex_generate
from .video_utils import pick_thumbnail_for_analysis


def parse_json_from_text(text):
    if not text:
        return None
    text = text.strip()

    def try_parse(candidate):
        candidate = candidate.strip()
        if candidate.lstrip().startswith("json"):
            candidate = candidate.lstrip()[4:].strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except Exception:
                return None
        return None

    if "```" in text:
        fence_parts = text.split("```")
        for idx in range(1, len(fence_parts), 2):
            parsed = try_parse(fence_parts[idx])
            if parsed is not None:
                return parsed

    return try_parse(text)


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
        try:
            data, mime = fetch_url_bytes(url)
        except Exception:
            continue
        if not data:
            continue
        seen.add(url)
        title = snippet.get("title") or f"{label_prefix} {idx}"
        label = f"{label_prefix} thumbnail for: {title}"
        samples.append((label, data, mime))
    return samples


def analyze_trends(channel_name, top_videos_raw, latest_videos_raw, top_videos_fmt,
                   latest_videos_fmt, metrics=None):
    budget = get_float("ANALYSIS_BUDGET_SECONDS", 20)
    deadline = time.monotonic() + max(budget, 5.0)
    metrics_summary = summarize_metrics(metrics)

    max_thumbs_env = os.environ.get("ANALYSIS_THUMBNAILS_MAX")
    if max_thumbs_env is not None:
        max_thumbs = get_int("ANALYSIS_THUMBNAILS_MAX", 6)
        per_group = max(1, max_thumbs // 2)
    else:
        per_group = get_int("ANALYSIS_THUMBNAILS_PER_GROUP", 10)

    title_sample_max = get_int("ANALYSIS_TITLE_SAMPLE_MAX", 50)

    def run_once(sample_max, thumbs_per_group, strict=False):
        prompt = build_trends_prompt(
            channel_name, top_videos_fmt, latest_videos_fmt, max_items=sample_max,
            strict=strict, metrics_summary=metrics_summary,
        )
        image_items = []
        image_items.extend(
            collect_thumbnail_samples(top_videos_raw, "Top", max_items=thumbs_per_group, deadline=deadline)
        )
        image_items.extend(
            collect_thumbnail_samples(latest_videos_raw, "Latest", max_items=thumbs_per_group, deadline=deadline)
        )
        if time.monotonic() > deadline:
            return None, "Analysis timed out before Vertex AI call."
        try:
            return vertex_generate(prompt, image_items=image_items), None
        except RuntimeError as exc:
            return None, str(exc)

    response_text, error = run_once(title_sample_max, per_group)
    if response_text is None and error and ("timed out" in error.lower() or "overloaded" in error.lower()):
        retry_sample_max = min(20, title_sample_max)
        retry_per_group = min(3, per_group)
        response_text, error = run_once(retry_sample_max, retry_per_group, strict=True)
    if response_text is None:
        return {"enabled": False, "reason": error or "Vertex AI did not return a response."}
    if not response_text:
        return {"enabled": False, "reason": "Vertex AI did not return a response."}

    parsed = parse_json_from_text(response_text)
    if not parsed:
        retry_sample_max = min(20, title_sample_max)
        retry_per_group = min(3, per_group)
        retry_text, retry_error = run_once(retry_sample_max, retry_per_group, strict=True)
        if retry_text:
            parsed = parse_json_from_text(retry_text)
            if parsed:
                response_text = retry_text
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
    parsed["strategyTips"] = normalize_list(parsed.get("strategyTips"))
    parsed["recommendedTags"] = normalize_list(parsed.get("recommendedTags"), max_items=15)
    design = parsed.get("thumbnailDesign")
    parsed["thumbnailDesign"] = design if isinstance(design, dict) else {}
    parsed["enabled"] = True
    return parsed
