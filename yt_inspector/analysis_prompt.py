"""Prompt construction for the Vertex AI title/thumbnail/strategy analysis.

Split from ``analysis`` so the orchestration logic stays focused on the API
call, retries and JSON parsing.
"""


def summarize_metrics(metrics):
    """Condense the competitor-analysis block into a compact prompt snippet.

    Grounds the AI's strategy advice in the real numbers already computed by
    ``competitor_metrics`` instead of letting the model guess.
    """
    if not metrics:
        return ""
    profile = metrics.get("profile", {})
    cadence = metrics.get("cadence", {})
    fmt = metrics.get("format", {})
    eng = metrics.get("engagement", {})
    seo = metrics.get("seo", {})
    top_tags = ", ".join(t.get("tag", "") for t in seo.get("topTags", [])[:10])
    return "\n".join([
        f"- Channel age: {profile.get('ageText', '-')}, sample of "
        f"{metrics.get('videoSampleSize', 0)} recent videos",
        f"- Views-to-sub ratio: {profile.get('viewsToSubRatio', 0)}% "
        f"({profile.get('viewsToSubLabel', '-')})",
        f"- Upload cadence: every {cadence.get('avgDaysBetween', 0)} days "
        f"({cadence.get('consistencyLabel', '-')}), peak day {cadence.get('peakDayLabel', '-')}",
        f"- Format: {fmt.get('shortsRatio', 0)}% shorts, avg long-form "
        f"{fmt.get('avgDurationMin', 0)} min",
        f"- Engagement: like {eng.get('likeRate', 0)}%, comment "
        f"{eng.get('commentRate', 0)}%, overall {eng.get('engagementRate', 0)}%",
        f"- Sponsor rate: {seo.get('sponsorRate', 0)}%",
        f"- Top tags used: {top_tags or 'none'}",
    ])


def build_trends_prompt(channel_name, top_videos, latest_videos, max_items=None,
                        strict=False, metrics_summary=""):
    """Build the analysis prompt for one channel."""
    if max_items:
        top_videos = top_videos[:max_items]
        latest_videos = latest_videos[:max_items]

    def lines_from(videos):
        lines = []
        for idx, video in enumerate(videos, 1):
            title = video.get("title") or "Untitled"
            views = video.get("views") or "0"
            published = video.get("publishedAt") or "unknown date"
            lines.append(f"{idx}. {title} | {views} views | {published}")
        return "\n".join(lines)

    instruction = (
        "You are a YouTube competitive strategist. Analyze the channel's titles, "
        "thumbnails and performance metrics.\n"
        "Return ONLY valid JSON with keys:\n"
        "- titleTrends (array of 3-6 bullet strings)\n"
        "- thumbnailTrends (array of 3-6 bullet strings)\n"
        "- titleFormula (string)\n"
        "- thumbnailFormula (string)\n"
        "- thumbnailDesign (object with string fields: characters, colorPalette, "
        "artStyle, typography, branding)\n"
        "- strategyTips (array of 4-6 actionable bullet strings advising a NEW "
        "channel on how to compete with this one, grounded in the metrics)\n"
        "- recommendedTags (array of 8-15 tag strings a new entrant should target)\n"
        "- caveats (string, optional)\n"
    )
    if strict:
        instruction += "Return a single JSON object only. No markdown, no code fences.\n"
    metrics_block = f"\nChannel performance metrics:\n{metrics_summary}\n" if metrics_summary else ""
    return (
        f"{instruction}\n"
        f"Channel: {channel_name}\n"
        f"{metrics_block}\n"
        "Top viewed videos:\n"
        f"{lines_from(top_videos)}\n\n"
        "Latest videos:\n"
        f"{lines_from(latest_videos)}\n\n"
        "Thumbnails are attached as images when available. If thumbnails are missing, "
        "focus on title patterns and note that thumbnail analysis is limited in caveats."
    )
