# Phase 02 — Secret Route + Template

**Priority:** High · **Status:** pending · **Depends on:** Phase 01

## Overview
Add the hidden `/secret` Flask route and a lean HTML template — a stripped clone of
`index.html`: no tabs, no Saved Channels, no Save/Airtable, no video grids.

## Related Code Files
**Modify:** `app.py`
**Create:** `templates/secret.html`

## Implementation Steps

### 1. Route — `app.py`
Add after the `index()` route:
```python
@app.route("/secret")
def secret():
    return render_template("secret.html")
```
No link to it from `index.html` or anywhere else (obscurity-only access).

### 2. `templates/secret.html`
Clone `index.html` structure (same `<head>`, fonts, `app.css`, bg orbs, header,
footer) with these differences:

**Remove:**
- `.tab-bar` and both `.tab-content` blocks (Saved Channels tab).
- `save-channel-btn`, `airtable-import`, `save-status`, `coming-soon`.
- Both `.video-section` blocks (Top Viewed Videos, Latest Videos).
- `country-card` and `avg-view-5-card` as standalone cards (data folded into new
  Channel Overview / Engagement sections).

**Hero panel** — keep only the inspect input:
```
label → #channel-input → #inspect-btn ; #status-text (no helper-actions)
```
Hero copy text updated to reflect competitor-analysis purpose.

**Results sections** (`#results.hidden`) — cards in spec-G order, each `class="card"`:
1. **Channel Overview** `#overview-card` — name, meta (handle · country · age),
   description, stats grid (subs / total views / total videos /
   avg views-lifetime / **views-to-sub ratio** badge), keyword + topic tags.
2. **Upload Cadence** `#cadence-card` — avg days between · consistency score+label ·
   peak hours KST (3 mini bars) · peak day of week.
3. **Content Format** `#format-card` — shorts/long ratio bar · avg long-form
   duration · duration trend (↑/↓) · avg title length · title-formula counts ·
   listicle ratio.
4. **Engagement** `#engagement-card` — avg views latest / top · like / comment /
   engagement rate · `#breakout-list` highlight box · `#underperform-list` (collapsed).
5. **SEO Intelligence** `#seo-card` — `#tag-cloud` · avg tags/video · sponsor rate ·
   `#revenue-streams` badges · paid-placement count. (No sponsor-brand list.)
6. **Title & Thumbnail Trends** `#analysis-card` — identical markup to `index.html`
   analysis card (reused as-is).

Each new section uses stable `id`s for `secret.js` to populate. Reuse existing
classes: `.card`, `.stat`, `.stats-grid`, `.metrics-grid`, `.tag`, `.muted`.

**Script:** `<script src="/static/secret.js"></script>` (not `app.js`).

`<title>` → `EMVN YouTube Competitor Inspector`.

## Todo
- [ ] `/secret` route in `app.py`
- [ ] `templates/secret.html` — lean clone, 6 result sections with stable ids
- [ ] No links to `/secret` anywhere; main `index.html` untouched

## Success Criteria
- `GET /secret` → 200, renders page; `GET /` unchanged.
- No tab bar, no save buttons, no video grids present in `/secret` DOM.
- All section container `id`s present and empty (populated in Phase 03).

## Risk Assessment
- Template drift from `index.html` — keep shared shell (header/footer/orbs) byte-identical to ease future style sync.

## Security Considerations
- `/secret` is obscurity-only — no sensitive data exposed beyond what `/api/inspect` already returns publicly. Acceptable per user decision.
