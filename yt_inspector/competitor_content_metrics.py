"""Content-format and engagement metrics for competitor analysis.

Split from ``competitor_metrics`` to keep each file focused and within size
limits. Input videos use the formatted shape from ``video_utils.format_video``
and are ordered latest-first.
"""
from .competitor_metrics_base import avg_views_latest, mean, safe_int
from .competitor_patterns import HOWTO_RE, LISTICLE_RE, NUMBER_START_RE, WHY_RE


def compute_format_metrics(videos):
    """Shorts ratio, duration stats and title-formula breakdown."""
    total = len(videos)
    if not total:
        return {
            "shortsRatio": 0.0, "shortsCount": 0, "longformCount": 0,
            "avgDurationMin": 0.0, "durationTrendMin": 0.0,
            "avgTitleLength": 0.0, "listicleRatio": 0.0,
            "titleFormulas": {"howTo": 0, "why": 0, "listicle": 0, "numberStart": 0},
        }
    durations = [safe_int(v.get("durationSeconds")) for v in videos]
    shorts = [d for d in durations if 0 < d < 60]
    longform = [d for d in durations if d >= 60]

    # Duration trend: newest window vs oldest window (minutes). Windows must not
    # overlap — use up to 10 each, or half the sample when fewer than 20 videos.
    half = min(10, total // 2)
    trend_min = (mean(durations[:half]) - mean(durations[-half:])) / 60 if half else 0.0

    titles = [(v.get("title") or "") for v in videos]
    formulas = {
        "howTo": sum(1 for t in titles if HOWTO_RE.search(t)),
        "why": sum(1 for t in titles if WHY_RE.search(t)),
        "listicle": sum(1 for t in titles if LISTICLE_RE.search(t)),
        "numberStart": sum(1 for t in titles if NUMBER_START_RE.search(t)),
    }
    return {
        "shortsRatio": round(len(shorts) / total * 100, 1),
        "shortsCount": len(shorts),
        "longformCount": len(longform),
        "avgDurationMin": round(mean(longform) / 60, 1) if longform else 0.0,
        "durationTrendMin": round(trend_min, 1),
        "avgTitleLength": round(mean([len(t) for t in titles]), 1),
        "listicleRatio": round(formulas["listicle"] / total * 100, 1),
        "titleFormulas": formulas,
    }


def _video_brief(video):
    return {
        "title": video.get("title"),
        "views": safe_int(video.get("views")),
        "url": video.get("url"),
    }


def compute_engagement_metrics(videos):
    """Engagement rates plus breakout / underperforming videos."""
    if not videos:
        return {
            "avgViewsLatest": 0, "avgViewsTop": 0,
            "likeRate": 0.0, "commentRate": 0.0, "engagementRate": 0.0,
            "breakoutVideos": [], "underperformVideos": [],
            "breakoutThreshold": 0, "underperformThreshold": 0,
        }
    all_views = [safe_int(v.get("views")) for v in videos]
    avg_sample = mean(all_views)

    like_rates, comment_rates, eng_rates = [], [], []
    for video in videos[:20]:
        views = safe_int(video.get("views"))
        if views <= 0:
            continue
        likes = safe_int(video.get("likes"))
        comments = safe_int(video.get("comments"))
        like_rates.append(likes / views * 100)
        comment_rates.append(comments / views * 100)
        eng_rates.append((likes + comments) / views * 100)

    # Breakout / underperform are measured against the whole sample's mean, so
    # the threshold and the scanned population stay consistent.
    breakout_threshold = avg_sample * 3
    underperform_threshold = avg_sample * 0.4
    breakout, underperform = [], []
    if avg_sample:
        breakout = sorted(
            (_video_brief(v) for v in videos if safe_int(v.get("views")) > breakout_threshold),
            key=lambda x: x["views"], reverse=True,
        )
        underperform = sorted(
            (_video_brief(v) for v in videos if safe_int(v.get("views")) < underperform_threshold),
            key=lambda x: x["views"],
        )

    return {
        "avgViewsLatest": avg_views_latest(videos),
        "avgViewsTop": int(mean(sorted(all_views, reverse=True)[:10])),
        "likeRate": round(mean(like_rates), 2),
        "commentRate": round(mean(comment_rates), 3),
        "engagementRate": round(mean(eng_rates), 2),
        "breakoutVideos": breakout[:3],
        "underperformVideos": underperform[:3],
        "breakoutThreshold": int(breakout_threshold),
        "underperformThreshold": int(underperform_threshold),
    }
