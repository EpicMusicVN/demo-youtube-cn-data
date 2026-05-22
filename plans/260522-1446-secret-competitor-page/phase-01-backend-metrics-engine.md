# Phase 01 — Backend Metrics Engine

**Priority:** High · **Status:** pending · **Depends on:** —

## Overview
Build the server-side computation layer for all spec-derived metrics, plus a lean
inspect path for `/secret`. Pure stdlib (`statistics`, `datetime`, `re`) — no new deps.

## Context
- Spec source: user-provided "YouTube Competitor Channel Data Spec" (sections A–H).
- `inspect_channel` already fetches: channel (snippet/contentDetails/brandingSettings/
  statistics/topicDetails) + up to 50 latest videos with full details.
- `format_video` (`video_utils.py:25`) already extracts `tags`, `description`,
  `views`, `likes`, `comments`, `durationSeconds`, `publishedAt`, `title`, `url`.
- **Missing raw field:** `paidProductPlacementDetails` — not in `videos.list` part.

## Related Code Files
**Create:**
- `yt_inspector/competitor_patterns.py` — regex/constants only (sponsor regex, brand list, revenue patterns, title-formula regex). ~40 lines.
- `yt_inspector/competitor_metrics.py` — computation logic. Target ≤200 lines; if exceeded, split SEO functions into `competitor_seo.py`.

**Modify:**
- `yt_inspector/service.py` — add `paidProductPlacementDetails` part; add `inspect_channel_lean`; add `competitorAnalysis` to `inspect_channel` result.
- `yt_inspector/video_utils.py` — `format_video` adds `hasPaidProductPlacement`.
- `app.py` — `/api/inspect` honors `?lean=1`.

## Implementation Steps

### 1. Raw data — `paidProductPlacementDetails`
- `service.py` `fetch_videos_details` (line ~152): change `part` to
  `"snippet,contentDetails,statistics,topicDetails,paidProductPlacementDetails"`.
  (videos.list = 1 quota unit regardless of parts — no quota change.)
- `video_utils.py` `format_video`: add
  `"hasPaidProductPlacement": item.get("paidProductPlacementDetails", {}).get("hasPaidProductPlacement", False)`.

### 2. `competitor_patterns.py` (constants)
```python
import re
SPONSOR_RE   = re.compile(r"sponsor|partner|ad:|code:|promo|affiliate|paid|kollab", re.I)
HOWTO_RE     = re.compile(r"^\s*how to\b", re.I)
QUESTION_RE  = re.compile(r"^\s*(why|what|how|when|who|is|are|can|should)\b.*\?|^\s*why\b", re.I)
LISTICLE_RE  = re.compile(r"\b(\d+)\s+(ways?|steps?|things?|tips?|reasons?)\b|^\s*top\s+\d+", re.I)
NUMBER_START_RE = re.compile(r"^\s*\d+")
REVENUE_PATTERNS = {
    "merch":      re.compile(r"merch|teespring|redbubble|/shop", re.I),
    "course":     re.compile(r"course|udemy|teachable|gumroad|skool", re.I),
    "discord":    re.compile(r"discord\.gg", re.I),
    "newsletter": re.compile(r"substack|newsletter", re.I),
    "membership": re.compile(r"patreon|/join|membership", re.I),
    "affiliate":  re.compile(r"amzn\.to|amazon.*associate|affiliate", re.I),
}
```
> **Decision:** no sponsor-brand extraction — only `sponsorRate`. No brand list.

### 3. `competitor_metrics.py` — `compute_competitor_metrics(channel, videos)`
`channel` = `result["channel"]` dict; `videos` = **full** formatted latest list (≤50).
Returns one dict with sub-objects. All helpers guard against empty list / zero
division / `None` / string-typed numbers (API returns counts as strings).

- **`_safe_int(v)`** — cast helper.
- **profile** — `ageText` (years+months from `channel.publishedAt`),
  `avgViewsLifetime` = `viewCount // videoCount`,
  `viewsToSubRatio` = `avgViewsLatest / subscriberCount * 100`,
  `viewsToSubLabel` = `engaged` (>10%) / `average` (5–10%) / `low` (<5%).
- **cadence** — parse `publishedAt` (`replace("Z","+00:00")` → `datetime.fromisoformat`),
  convert to KST `timezone(timedelta(hours=9))`. `avgDaysBetween` = mean of sorted-desc
  diffs; `consistencyScore` = `statistics.pstdev`; label `Rất đều` (<1) / `Đều` (1–3) /
  `Không đều` (>3). `peakHoursKST` = top-3 hours by histogram; `peakDayLabel` =
  most-common weekday → `T2..CN`.
- **format** — `shortsRatio` = `count(durationSeconds < 60) / total * 100`;
  `avgDurationMin` over long-form (>60s); `durationTrendMin` = avgDur(latest10) −
  avgDur(oldest10); `avgTitleLength` (chars); `titleFormulas` counts via patterns;
  `listicleRatio`.
- **engagement** — `avgViewsLatest` (latest 10), `avgViewsTop` (top 10 by views in
  sample), `likeRate`/`commentRate`/`engagementRate` (mean over latest 20),
  `breakoutVideos` (views > 3× avgViewsLatest, top 3, `{title,views,url}`),
  `underperformVideos` (views < 0.4× avgViewsLatest, up to 3), thresholds.
- **seo** — `topTags` (aggregate `tags`, top 20 `{tag,count}`), `avgTagsPerVideo`,
  `sponsorRate` (% descriptions matching `SPONSOR_RE`), `hasSponsor`,
  `revenueStreams` (`REVENUE_PATTERNS` over all descriptions → bool map),
  `paidPlacementCount` (count `hasPaidProductPlacement`).
  *No `sponsorBrands`* — per user decision.
- Top-level: `videoSampleSize`.

### 4. `inspect_channel_lean(target, enable_analysis=True)` in `service.py`
Reuses existing helpers — keep short (~45 lines):
1. `resolve_channel_id` → `fetch_channel_details`.
2. `fetch_latest_videos(uploads, max_results=fetch_max)` → `fetch_videos_details` → `format_video`.
3. Build `channel` dict (same shape as `inspect_channel`).
4. `competitorAnalysis = compute_competitor_metrics(channel, latest_formatted)`.
5. If `enable_analysis` and `VERTEX_API_KEY`: `analyze_trends(name, [], latest_raw,
   [], latest_formatted)` — **empty top lists**. AI then analyzes **10 thumbnails**
   (`ANALYSIS_THUMBNAILS_PER_GROUP` default, latest group only) + **50 titles**
   (`ANALYSIS_TITLE_SAMPLE_MAX` default) from latest uploads. No change to `analysis.py`.
6. Return `{"channel": channel, "competitorAnalysis": ..., "analysis": ...}`.
**Skips** `fetch_top_viewed_videos` (`/search`, ~100 units each) and UUSH playlist.

### 5. Wire normal path + route
- `inspect_channel`: after building `result`, add
  `result["competitorAnalysis"] = compute_competitor_metrics(result["channel"], latest_formatted)`
  (use the **untruncated** `latest_formatted`, before `[:output_max]`).
- `app.py` `api_inspect`: read `lean = request.args.get("lean","")` → if truthy call
  `inspect_channel_lean(...)` else `inspect_channel(...)`.

## Todo
- [ ] `paidProductPlacementDetails` part + `format_video` field
- [ ] `competitor_patterns.py`
- [ ] `competitor_metrics.py` — profile / cadence / format / engagement / seo
- [ ] `inspect_channel_lean` in `service.py`
- [ ] `competitorAnalysis` in `inspect_channel`
- [ ] `?lean=1` branch in `app.py`
- [ ] `python3 -c "import yt_inspector.service"` compiles clean

## Success Criteria
- `compute_competitor_metrics` returns full dict for a sample channel; no exceptions
  on empty videos / zero subs / null tags / missing `publishedAt`.
- `/api/inspect?url=...&lean=1` returns `{channel, competitorAnalysis, analysis}` and
  makes **no** `/search` call (verify via reduced latency / quota).
- `/api/inspect?url=...` (normal) unchanged except extra `competitorAnalysis` key.

## Risk Assessment
- **`datetime.fromisoformat` + 'Z'** — pre-3.11 rejects `Z`; mitigation: `replace("Z","+00:00")`.
- **String-typed API counts** — always `_safe_int` before math.
- **File size** — if `competitor_metrics.py` > 200 lines, split SEO into `competitor_seo.py`.

## Resolved Decisions
1. `?lean=1` **skips** top-viewed `/search` + UUSH — confirmed. Lands at spec's ~11 quota units.
2. Sponsor detection — **`sponsorRate` only**, no brand-name extraction (no curated list, no AI).
3. AI analysis on `/secret` — **10 thumbnails + 50 titles** from latest uploads.
