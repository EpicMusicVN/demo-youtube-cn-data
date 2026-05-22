"""Compute competitor-analysis metrics from channel + video data.

Pure standard library. Input video dicts use the formatted shape produced by
``video_utils.format_video`` and are ordered latest-first. Every function guards
against empty input, zero division, ``None`` values, and string-typed API counts
(the YouTube API returns view/like/comment counts as strings).

Format/engagement metrics live in ``competitor_content_metrics`` and SEO/tag
metrics in ``competitor_seo`` to keep each file focused.
"""
import statistics
from datetime import datetime, timedelta, timezone

from .competitor_content_metrics import compute_engagement_metrics, compute_format_metrics
from .competitor_metrics_base import avg_views_latest, safe_int
from .competitor_seo import compute_seo_metrics

# Korea Standard Time — spec requires cadence timestamps converted to KST.
KST = timezone(timedelta(hours=9))
# Python ``date.weekday()``: 0=Monday .. 6=Sunday.
WEEKDAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _parse_dt(value):
    """Parse a YouTube ISO-8601 timestamp into a KST-aware datetime, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def compute_competitor_metrics(channel, videos):
    """Return the full competitor-analysis block for one channel.

    ``channel`` is the result["channel"] dict; ``videos`` is the *untruncated*
    formatted latest-uploads list (up to 50).
    """
    videos = videos or []
    return {
        "videoSampleSize": len(videos),
        "profile": _profile_metrics(channel or {}, videos),
        "cadence": _cadence_metrics(videos),
        "format": compute_format_metrics(videos),
        "engagement": compute_engagement_metrics(videos),
        "seo": compute_seo_metrics(videos),
    }


# --------------------------------------------------------------------------
# A. Channel profile
# --------------------------------------------------------------------------
def _channel_age(published_at):
    """Return (human text, total months) for a channel creation date."""
    dt = _parse_dt(published_at)
    if not dt:
        return "-", 0
    now = datetime.now(KST)
    months = (now.year - dt.year) * 12 + (now.month - dt.month)
    if now.day < dt.day:
        months -= 1
    months = max(months, 0)
    years, rem = divmod(months, 12)
    text = (f"{years}y " if years else "") + f"{rem}m"
    return text, months


def _profile_metrics(channel, videos):
    stats = channel.get("statistics", {}) or {}
    view_count = safe_int(stats.get("viewCount"))
    video_count = safe_int(stats.get("videoCount"))
    sub_count = safe_int(stats.get("subscriberCount"))

    avg_lifetime = view_count // video_count if video_count else 0
    avg_latest = avg_views_latest(videos)
    ratio = (avg_latest / sub_count * 100) if sub_count else 0.0
    if ratio >= 10:
        ratio_label = "engaged"
    elif ratio >= 5:
        ratio_label = "average"
    else:
        ratio_label = "low"

    age_text, age_months = _channel_age(channel.get("publishedAt"))
    return {
        "ageText": age_text,
        "ageMonths": age_months,
        "avgViewsLifetime": avg_lifetime,
        "viewsToSubRatio": round(ratio, 2),
        "viewsToSubLabel": ratio_label,
    }


# --------------------------------------------------------------------------
# B. Upload cadence & timing (all timestamps in KST)
# --------------------------------------------------------------------------
def _cadence_metrics(videos):
    dates = sorted(
        (d for d in (_parse_dt(v.get("publishedAt")) for v in videos) if d),
        reverse=True,
    )
    if len(dates) < 2:
        return {
            "avgDaysBetween": 0.0,
            "consistencyScore": 0.0,
            "consistencyLabel": "-",
            "peakHoursKST": [],
            "peakDayLabel": "-",
        }

    gaps = [(dates[i] - dates[i + 1]).total_seconds() / 86400 for i in range(len(dates) - 1)]
    consistency = statistics.pstdev(gaps) if len(gaps) > 1 else 0.0
    if consistency < 1:
        label = "Rất đều"
    elif consistency <= 3:
        label = "Đều"
    else:
        label = "Không đều"

    hour_counts = {}
    day_counts = {}
    for d in dates:
        hour_counts[d.hour] = hour_counts.get(d.hour, 0) + 1
        day_counts[d.weekday()] = day_counts.get(d.weekday(), 0) + 1
    peak_hours = sorted(hour_counts.items(), key=lambda kv: kv[1], reverse=True)[:3]
    peak_day = max(day_counts.items(), key=lambda kv: kv[1])[0]

    return {
        "avgDaysBetween": round(statistics.fmean(gaps), 1),
        "consistencyScore": round(consistency, 2),
        "consistencyLabel": label,
        "peakHoursKST": [{"hour": h, "count": c} for h, c in peak_hours],
        "peakDayLabel": WEEKDAY_LABELS[peak_day],
    }
