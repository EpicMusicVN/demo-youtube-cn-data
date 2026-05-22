# Phase 04 — Tests, Verification, Docs

**Priority:** Medium · **Status:** pending · **Depends on:** Phase 01–03

## Overview
Unit-test the metrics engine (the error-prone math), verify both pages end-to-end,
update docs.

## Related Code Files
**Create:** `tests/test_competitor_metrics.py`
**Modify:** `README.md`
(`requirements.txt` — add `pytest` only if not already resolvable; tests can also
run via `python3 -m unittest` with stdlib to avoid a new dep — prefer stdlib.)

## Implementation Steps

### 1. Unit tests — `tests/test_competitor_metrics.py`
Stdlib `unittest` (no new dependency). Build fixture lists of formatted videos.
Cover `compute_competitor_metrics`:
- **Happy path** — 50 videos, all fields → every sub-object populated, types correct.
- **Empty list** — `videos=[]` → no exception, zeros / empty lists / `-` labels.
- **Zero division** — `subscriberCount="0"`, `videoCount="0"` → no crash, ratio 0.
- **Null/missing** — `tags` missing, `description` `None`, `publishedAt` missing/bad.
- **String counts** — `views`/`likes` as strings → math still correct.
- **Cadence** — known `publishedAt` set → assert `avgDaysBetween`, KST peak hour,
  `consistencyLabel` boundaries (<1, 1–3, >3).
- **Format** — mix of <60s and >60s → `shortsRatio`, `avgDurationMin`.
- **Engagement** — crafted views → `breakoutVideos` / `underperformVideos` thresholds.
- **SEO** — descriptions with/without sponsor + revenue keywords → `sponsorRate`,
  `revenueStreams`, `sponsorBrands`, `topTags` ordering.

### 2. End-to-end verification (manual / `tester` agent)
- `python3 app.py` → `GET /secret` 200; `GET /` 200 unchanged.
- `/api/inspect?url=<real channel>&lean=1` → JSON has `channel` +
  `competitorAnalysis` (all 5 sub-objects) + `analysis`; confirm **no** `/search`
  call made (lean path).
- `/api/inspect?url=<real channel>` → unchanged shape + extra `competitorAnalysis`.
- Browser `/secret`: paste channel → 6 sections populate; test a sparse channel
  (few videos, no tags) → graceful.
- Browser `/`: confirm main page identical (tabs, video grids, save all work).

### 3. Docs
- `README.md` — add a "Secret page" subsection: `/secret` route, lean inspect
  (`?lean=1`), what it shows, that it has no link by design.
- No `docs/` files exist yet — do **not** scaffold the full `docs/` set for this
  feature; a README note is sufficient (KISS).

## Todo
- [ ] `tests/test_competitor_metrics.py` — all cases above
- [ ] `python3 -m unittest discover tests` → all pass
- [ ] E2E: `/secret` + `/` verified in browser
- [ ] Lean path confirmed (no `/search`)
- [ ] `README.md` updated

## Success Criteria
- All unit tests pass; no failures skipped.
- Both pages verified; main page regression-free.
- Spec sections A–E metrics all visible on `/secret` for a real channel.

## Risk Assessment
- Live YouTube API needed for E2E — requires valid `YOUTUBE_API_KEY` + quota; unit
  tests use fixtures so they run offline / in CI.
- Quota: each `/secret` inspect ≈ 11 units (channels + playlistItems + videos).

## Next Steps
- Optional follow-up: extract shared JS helpers to `static/shared.js` (DRY) — separate small refactor.
