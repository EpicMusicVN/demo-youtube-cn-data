# Phase 03 — Frontend Rendering (JS + CSS)

**Priority:** High · **Status:** pending · **Depends on:** Phase 01, 02

## Overview
Build `static/secret.js` to fetch `/api/inspect?lean=1` and render the 6 result
sections; extend `static/app.css` with styles for the new metric widgets.

## Related Code Files
**Create:** `static/secret.js`
**Modify:** `static/app.css` (append-only block)

## Implementation Steps

### 1. `static/secret.js` (self-contained)
- **Helpers** — copy the small pure utilities from `app.js` (`formatNumber`,
  `formatDate`, `trimText`, `secondsToReadable`, `setStatus`, `makeStat`).
  *Accepted KISS tradeoff:* ~55 lines duplicated to keep `/secret` fully isolated
  from the working main page (no edits to `app.js`/`index.html`).
- **`inspectChannel()`** — `fetch('/api/inspect?lean=1&url=' + encodeURIComponent(url))`,
  on success call the section renderers, reveal `#results`.
- **Renderers** (one per section, read `payload.competitorAnalysis`):
  - `renderOverview(channel, profile)` — meta line incl. `profile.ageText`;
    stats grid; `views-to-sub` value with badge class from `viewsToSubLabel`
    (`badge-good`/`badge-warn`/`badge-bad`); keyword + topic tags (reuse logic).
  - `renderCadence(cadence)` — stats + 3 peak-hour mini bars (`div` width = count/max).
  - `renderFormat(format)` — ratio bar (shorts vs long), duration trend arrow,
    title-formula counts, listicle ratio.
  - `renderEngagement(engagement)` — rate stats; breakout list (title + views +
    link, highlighted); underperform list inside a `<details>` collapse.
  - `renderSeo(seo)` — tag cloud (`font-size` scaled by `count`), avg tags,
    sponsor rate, revenue-stream badges (active vs muted), paid-placement count.
  - `renderAnalysis(analysis)` — port verbatim from `app.js` (`normalizeList` +
    `renderList`); handles `enabled:false` and `raw` fallbacks.
- **Empty/edge states** — every renderer shows `-` or "No data" when its metric is
  missing; guard against `competitorAnalysis` absent (older payloads).
- No tabs, no saved-channels, no save logic.

### 2. `static/app.css` — appended `/* === Secret page === */` block
Reuse `.card`, `.stat`, `.stats-grid`, `.tag`, EMVN CSS vars. Add:
- `.badge-good` / `.badge-warn` / `.badge-bad` — pill colors (green / gold / coral).
- `.ratio-bar` + `.ratio-bar__fill` — horizontal shorts/long split.
- `.mini-bar` row — peak-hour bars (`--emvn-blue-2`).
- `.tag-cloud` + `.tag-cloud__item` — inline-wrap, size set inline by JS.
- `.revenue-badge` (`.is-active` vs muted), `.trend-up` / `.trend-down`.
- `.breakout-box` (gold-tinted), `.underperform` `<details>` styling.
No charting library — CSS-only visualizations (YAGNI).

## Todo
- [ ] `secret.js` helpers + `inspectChannel` (lean fetch)
- [ ] 6 section renderers + edge-state guards
- [ ] `renderAnalysis` ported from `app.js`
- [ ] `app.css` secret-page style block
- [ ] Manual: paste a channel URL on `/secret` → all sections populate

## Success Criteria
- Paste a real channel link on `/secret` → all 6 sections render with live data.
- Badges/colors reflect thresholds (views-to-sub, consistency, trend direction).
- Channel with no tags / no sponsors / few videos renders gracefully (no JS errors).
- Main page `/` visually + functionally identical to before.

## Risk Assessment
- **Helper duplication** vs `app.js` — accepted; if code-reviewer flags, future
  refactor to `static/shared.js` (out of scope here).
- Tag cloud with hundreds of unique tags — cap at top 20 (already done backend).

## Security Considerations
- All rendered values via `textContent` / controlled DOM creation — no `innerHTML`
  with API data (XSS-safe), matching `app.js` pattern. `makeStat` uses `innerHTML`
  with **static labels only** — never interpolate channel/video strings into it.
