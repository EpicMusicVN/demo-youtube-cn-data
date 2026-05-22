"""Shared low-level helpers for the competitor-metrics modules.

Kept in their own module so ``competitor_metrics`` and
``competitor_content_metrics`` can both import them without a circular import.
"""
import statistics


def safe_int(value):
    """Cast API values (often strings or None) to int, defaulting to 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def mean(values):
    """Arithmetic mean, or 0.0 for an empty sequence."""
    return statistics.fmean(values) if values else 0.0


def avg_views_latest(videos, count=10):
    """Average view count of the ``count`` most recent videos."""
    views = [safe_int(v.get("views")) for v in videos[:count]]
    return int(mean(views))
