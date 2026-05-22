# Code Review — /secret Competitor-Analysis Page

Date: 2026-05-22 | Reviewer: code-reviewer | Branch: main
Scope: 9 files (4 new py/js/html, 5 modified). ~1195 LOC across new py + secret.js.

## Overall Assessment

Solid, defensive work. Metric math guards zero-division and `None`/string inputs
well; `secret.js` uses `textContent`/DOM construction almost everywhere — XSS
surface is small. `_build_channel_dict` correctly preserves main-page output.
No Critical issues. A handful of real correctness bugs (High/Medium) that will
surface on real-world data, plus DRY and file-size nits.

---

## Critical

None.

---

## High

### H1. Duration-trend double-counts videos when sample < 20 — misleading metric
`competitor_metrics.py:179`
```python
trend_min = (_mean(durations[:10]) - _mean(durations[-10:])) / 60
```
When the channel has 10–19 uploads, `durations[:10]` and `durations[-10:]`
**overlap** — the same videos are in both the "newest" and "oldest" windows.
With exactly 10 videos the two slices are identical, so the trend is always
`0.0` regardless of actual change. With 11–19 videos the trend is diluted by
shared videos. Scout flagged this as a target area and it is a real bug.
- Impact: "Duration Trend" shows flat/under-stated for any channel with <20
  uploads (common for newer competitors — the exact use case).
- Fix: require a minimum sample and non-overlapping windows, e.g.
  `if total >= 6: half = min(10, total // 2); trend = (_mean(durations[:half]) - _mean(durations[-half:]))/60 else 0.0`.

### H2. `breakoutThreshold` excludes legitimate breakouts via strict `>`
`competitor_metrics.py:233,238`
```python
breakout_threshold = avg_latest * 3
... if _safe_int(v.get("views")) > breakout_threshold
```
`avg_latest` is computed only from the latest 10 (`_avg_views_latest`), but
`breakout`/`underperform` scan **all ~50** videos. A channel whose latest 10
happen to be low-view will flag most of its back catalogue as "breakout"; a
channel with a few viral latest videos inflates `avg_latest` and flags almost
nothing. The threshold base and the scanned population are mismatched.
- Impact: breakout/underperform lists are unstable and can be nonsensical
  (e.g. 30 "breakout" videos, or zero) depending on which 10 are newest.
- Fix: base the threshold on the **full sample** mean (or median), not just
  latest-10. The same `avg_latest` is reused as a display stat where latest-10
  is correct — separate the two concepts.

### H3. `renderFormat` long-form % can render >100% or negative bar
`secret.js:144-148`
```python
const shortPct = fmt.shortsRatio || 0;
const longPct = 100 - shortPct;
```
`shortsRatio` counts only `0 < d < 60` (`competitor_metrics.py:176`).
`longformCount` counts `d >= 60`. Videos with `durationSeconds == 0` (live
streams, premieres, unparseable durations, or `None`→0 via `_safe_int`) are in
**neither** bucket. So `shortsCount + longformCount` can be < `total`, and
`shortsRatio` is a fraction of `total` that does not complement the actual
long-form fraction. `longPct = 100 - shortPct` then misrepresents reality and
the ratio bar fills are wrong (e.g. shorts 10% of total but 30% of total are
0-duration → bar claims 90% long).
- Impact: visibly wrong Shorts-vs-Long bar on channels with live/premiere
  content (very common for music channels — this is a music-competitor tool).
- Fix: derive `longPct` from `longformCount/total` server-side, or have the
  backend return both ratios explicitly and a third "other" bucket.

---

## Medium

### M1. `peakDay` tie-break is non-deterministic across equal-count days
`competitor_metrics.py:152` — `max(day_counts.items(), key=...)` returns the
first max encountered, but `day_counts` insertion order follows video order,
which follows API order. Two channels with the same upload pattern can report
different peak days. Low severity but the metric claims more precision than it
has. Consider tie-breaking by weekday index for determinism.

### M2. KST channel-age `now.day < dt.day` is an approximation
`competitor_metrics.py:86` — month-diff with a single day-of-month compare is
off by up to a day at month boundaries (e.g. created Jan-31, now Mar-01).
Cosmetic — `ageText` is display-only — but worth a comment noting the
approximation, or use `dateutil.relativedelta` if already available.

### M3. `commentRate`/`likeRate` averaged over latest-20 only — inconsistent window
`competitor_metrics.py:223` engagement rates use `videos[:20]`, while
`avgViewsTop` uses all 50 and `avgViewsLatest` uses 10. Three different windows
in one section with no UI label explaining which. Not wrong, but the dashboard
implies these are comparable. Document the window in the label or unify.

### M4. `format-ratio` `seg.pct <= 0` hides a 0% segment but `toFixed` mismatch
`secret.js:147-148` — short label uses raw `shortPct` (already rounded to 1dp
server-side), long label uses `longPct.toFixed(1)`. If `shortsRatio` is e.g.
`33.3`, long shows `66.7` — fine. But if backend ever returns an int, formats
diverge. Minor cosmetic inconsistency; pick one formatting path.

### M5. File size — `competitor_metrics.py` is 256 lines, over the 200-line guideline
Project rule (`development-rules.md`) caps files at ~200 LOC. SEO was already
split out; cadence (`_cadence_metrics`) or engagement (`_engagement_metrics`)
could move to a `competitor_engagement.py` to comply. Not a runtime issue.

### M6. `save_channel` failure is silent on the client
`secret.js:363-370` — `saveChannel` does `await fetch(...)` but never checks
`response.ok`. A 400/500 (missing channel id, DB down) still shows "Saved!".
The main page may have the same bug, but the secret page is new code and
should check `if (!response.ok) throw ...` like `inspectChannel` does.

---

## Low

### L1. `deleteSavedChannel` ignores `response.ok`
`secret.js:459-465` — a 404 ("Channel not found") still triggers a silent
`loadSavedChannels()` with no user feedback. Minor; reloading masks it.

### L2. Pagination clamp is correct but `savedPage` can briefly go negative/over
`secret.js:488-494` — prev/next mutate `savedPage` unconditionally then call
`renderSavedPage()`, which re-clamps at line 430. Functionally fine (clamp
saves it), but cleaner to clamp in the handlers so state never holds an invalid
value. Delete-last-item-on-last-page is handled correctly: `loadSavedChannels`
resets `savedPage = 0`, and the clamp covers the non-reset path.

### L3. `normalizeList` splits AI strings on `-` — corrupts hyphenated words
`secret.js:271` — `value.split(/\n|\r|•|-/)` splits on every hyphen, so an AI
caveat like "long-form" becomes "long"/"form" as separate list items. Use
`\n`, `\r`, `•` only, or split on `- ` (hyphen+space) for bullet markers.

### L4. `competitor_patterns.SPONSOR_RE` over-broad — `ad:` / `paid` / `partner`
`competitor_patterns.py:9` — `paid` matches "unpaid", "paid off", etc.;
`partner` matches "partnership announcement" unrelated to sponsorship. Expect
inflated `sponsorRate` on real descriptions. Tighten to word boundaries
(`\bpaid\b`) and consider dropping the noisiest tokens. Functional, just noisy.

### L5. `_avg_views_latest` slices `videos[:10]` assuming latest-first ordering
`competitor_metrics.py:50-53` — relies on `reorder_videos` preserving
playlist (latest-first) order. True today, but undocumented coupling; a one-line
comment ("videos must be latest-first") would prevent a future regression.
Same assumption in `_format_metrics` trend slices.

### L6. `viewSavedChannel` renders `full_payload` which may be `null`
`secret.js:376-383` — `renderPayload` handles `payload.channel || {}`, so a
saved row with `full_payload = null` (older rows pre-`full_payload` column, see
`db.py:33` migration) would render an empty dashboard silently. `viewSavedChannel`
guards `if (!payload) return` — good — but then nothing happens and the user
gets no feedback. Add a status message for that case.

---

## Verified Good

- **XSS**: All API-derived strings (`channel.name`, descriptions, titles, tags,
  AI output) go through `textContent` or `document.createElement`. The only
  `innerHTML` uses (`clear()`, `'<span class="muted">...'`, `'<p class="muted">'`)
  write **static literal** strings — no interpolation of untrusted data. Safe.
- **`_build_channel_dict` refactor**: extracted dict is byte-identical to the
  prior inline construction; `inspect_channel` output keys unchanged, plus the
  new `competitorAnalysis`. Main page contract preserved.
- **Zero-division**: every ratio guarded (`if total`, `if sub_count`,
  `if video_count`, `views <= 0: continue`, `_mean` returns 0.0 on empty).
- **`<2` videos cadence**: early-return path is correct and tested.
- **String-typed counts**: `_safe_int` consistently applied; tested.
- **DB layer**: parameterized queries throughout — no SQL injection. `delete`
  uses `rowcount` for 404 correctly.
- **Lean path**: skips `/search` + UUSH as claimed; AI gets latest-only.

---

## Recommended Actions (priority order)

1. **H1** — fix duration-trend overlap for <20-video channels.
2. **H2** — base breakout/underperform threshold on full-sample mean, not latest-10.
3. **H3** — fix Shorts-vs-Long bar to account for 0-duration videos.
4. **M6** — check `response.ok` in `saveChannel`.
5. **M5** — split `competitor_metrics.py` to satisfy 200-line guideline.
6. L1–L6 — cleanup as capacity allows.

---

## Unresolved Questions

1. Is the "Duration Trend" expected to be meaningful for channels with <20
   uploads, or is "flat" acceptable there? (Affects H1 fix strictness.)
2. Should `breakoutVideos` scan all 50 videos or only the latest 10? The
   threshold base implies latest-10; the scan implies all-50 (H2).
3. Are 0-duration videos (live/premiere) expected in the latest-uploads sample,
   or filtered upstream? Confirms H3 severity.
4. `/secret` is obscurity-only with no auth — intentional, but `/api/inspect`
   is fully public regardless. No new exposure from this feature, noted only
   for completeness.
