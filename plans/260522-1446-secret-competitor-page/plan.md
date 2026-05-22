---
title: Secret Competitor-Analysis Page (/secret)
created: 2026-05-22 14:46
status: completed
branch: feat-secret-page
blockedBy: []
blocks: []
---

# Secret Competitor-Analysis Page (`/secret`)

## Goal
Add a hidden `/secret` page — a lean clone of the main inspector (paste URL → inspect)
that **drops the Top Viewed / Latest video grids** and instead surfaces a full
competitor-analysis dashboard (cadence, format, engagement, SEO/tags, sponsor/revenue)
per the YouTube Competitor Channel Data Spec.

## Key Decisions (from user)
- **Access:** path route `/secret`, no link from anywhere (obscurity only).
- **Chrome:** Inspect + Saved Channels tabs, Save Channel button (Airtable omitted).
  *(Revised post-implementation — initially lean; Save + paginated Saved Channels
  re-added per follow-up request.)*
- **Saved list:** client-side pagination (6/page) so the card layout doesn't break.
- **Metrics compute:** *backend* — new `yt_inspector/competitor_metrics.py`, returned in JSON.
- **Endpoint:** reuse `/api/inspect` with `?lean=1` → skips the costly `/search` top-viewed
  calls (~100+ quota units) since `/secret` shows no top-viewed grid. Lands at spec's ~11 units.
- `competitorAnalysis` also added to the normal `/api/inspect` response (harmless; main page ignores it).

## Phases

| # | Phase | Status | Depends on |
|---|-------|--------|-----------|
| 01 | [Backend metrics engine](phase-01-backend-metrics-engine.md) | completed | — |
| 02 | [Secret route + template](phase-02-secret-route-and-template.md) | completed | 01 |
| 03 | [Frontend rendering (JS + CSS)](phase-03-frontend-rendering.md) | completed | 01, 02 |
| 04 | [Tests, verification, docs](phase-04-tests-and-verification.md) | completed | 01–03 |

## Files Touched
**Create:** `yt_inspector/competitor_metrics.py`, `yt_inspector/competitor_patterns.py`,
`templates/secret.html`, `static/secret.js`, `tests/test_competitor_metrics.py`
**Modify:** `app.py`, `yt_inspector/service.py`, `yt_inspector/video_utils.py`,
`static/app.css`, `README.md`

## Out of Scope
- No changes to main page (`/`, `index.html`, `app.js`) UI/behavior.
- No charting library (CSS-only mini visualizations).
- No auth/passphrase on `/secret` beyond the obscure path.
- Airtable import, persistence of competitor metrics to DB.

## Resolved Decisions
- `?lean=1` skips top-viewed `/search` + UUSH → ~11 quota units (spec budget).
- Sponsor detection = `sponsorRate` only (no brand-name list).
- AI thumbnail/title analysis = 10 thumbnails + 50 titles from latest uploads.
