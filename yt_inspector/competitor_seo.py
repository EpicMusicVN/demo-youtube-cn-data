"""SEO & tag intelligence metrics for competitor analysis.

Split from ``competitor_metrics`` to keep each file focused and within size
limits. Input videos use the formatted shape from ``video_utils.format_video``.
"""
from .competitor_patterns import REVENUE_PATTERNS, SPONSOR_RE


def compute_seo_metrics(videos):
    """Aggregate tags, sponsor signals and revenue streams across ``videos``."""
    total = len(videos)
    tag_counts = {}
    tag_total = 0
    for video in videos:
        tags = video.get("tags") or []
        tag_total += len(tags)
        for tag in tags:
            key = str(tag).strip()
            if key:
                tag_counts[key] = tag_counts.get(key, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]

    descriptions = [(v.get("description") or "") for v in videos]
    sponsor_hits = sum(1 for desc in descriptions if SPONSOR_RE.search(desc))
    all_desc = "\n".join(descriptions)
    revenue_streams = {
        name: bool(pattern.search(all_desc)) for name, pattern in REVENUE_PATTERNS.items()
    }
    paid_placement = sum(1 for v in videos if v.get("hasPaidProductPlacement"))

    return {
        "topTags": [{"tag": tag, "count": count} for tag, count in top_tags],
        "avgTagsPerVideo": round(tag_total / total, 1) if total else 0.0,
        "sponsorRate": round(sponsor_hits / total * 100, 1) if total else 0.0,
        "hasSponsor": sponsor_hits > 0,
        "revenueStreams": revenue_streams,
        "paidPlacementCount": paid_placement,
    }
