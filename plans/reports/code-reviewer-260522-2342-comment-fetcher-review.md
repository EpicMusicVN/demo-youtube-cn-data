# Code Review — YouTube Comment Fetcher

Date: 2026-05-22
Reviewer: code-reviewer (adversarial)
Scope: `yt_inspector/comments.py`, `templates/comments.html`, `static/comments.js`,
`tests/test_comments.py`, `app.py`, `templates/secret.html`

## Overall Assessment

Solid, small feature. XSS surface is clean (every API-derived string goes through
`textContent`). No `innerHTML` with untrusted data. Pagination loop terminates
correctly. The issues below are real but mostly Medium/Low — one High
(pagination quota waste), one security-leak concern, and a few real-world data
edge cases.

---

## Critical

None.

---

## High

### H1 — Pagination over-fetches and burns quota when `max_results` < 100
`comments.py:84` — `maxResults` is set to `min(100, max_results - len(comments))`.
That clamp is correct for the *page size*, but the loop keeps requesting pages
until `len(comments) >= max_results`. For `max=500` that is up to 5 page calls
(5 quota units). Fine. The real problem: the YouTube API frequently returns
*fewer* items than `maxResults` requested even when more exist, and it can also
return items whose `topLevelComment` is missing. Each loop iteration that yields
0 usable items but a non-null `nextPageToken` still counts toward quota, and if
the API returns a stable `nextPageToken` with empty `items` (rare but observed
on heavily-moderated videos) the loop will spin page-after-page until the token
finally goes null — potentially dozens of quota units for one user request.

Recommendation: add a hard page cap as a safety bound:
```python
pages = 0
MAX_PAGES = 10
while len(comments) < max_results and pages < MAX_PAGES:
    ...
    pages += 1
```
This bounds quota regardless of API behavior. The current code's only
termination guarantee is `nextPageToken is None`, which the API controls.

### H2 — Raw YouTube API error body leaked to the client
`comments.py:48-56` `_friendly_error` only rewrites three known cases; the final
`return message` passes the *raw* exception string through. From
`youtube_api.py:31` that string is `HTTP {code} error: {body}` where `body` is
the **full JSON error response from Google**. On a quota-exceeded (403
`quotaExceeded`) or bad-key (400 `keyInvalid`) error, that response can include
the API project context and the reason code, and the full body is returned to
the browser via `app.py:84` `jsonify({"error": str(exc)})`.

Impact: internal/infra detail leaks to any user of `/api/comments`. Not a
credential leak (the key itself is in the URL, not the body), but it exposes
quota state and project error reasons to an unauthenticated endpoint.

Recommendation: make `_friendly_error` fail *closed* — map known cases, and for
anything else return a generic `"Could not fetch comments — try again later."`
Log the raw error server-side instead of returning it.

---

## Medium

### M1 — `resolve_video_id` silently mis-resolves channel/playlist URLs
`comments.py:22-35`. `extract_video_id_from_url` (`parsers.py:6-17`) returns
`qs["v"][0]` whenever a `v` query param exists — with **no length/charset
validation**. A URL like `youtube.com/playlist?list=PL...&v=garbage` or any URL
with a stray `?v=` returns that raw value. `resolve_video_id` then guards it
with `_VIDEO_ID_RE.match(vid)` (line 30) — good, that catches malformed IDs.
But a `v` param that *is* 11 valid chars but belongs to a different context is
accepted blindly. Low exploit value, but worth noting the guard is charset-only,
not semantic. Acceptable as-is; flagging because the test suite
(`test_invalid_inputs`) does not cover the `?v=` -with-junk case.

### M2 — Comment count shown to user can mislead on partial fetches
`comments.js:171` reports `Done — ${payload.count} comments fetched.` and
`renderComments` line 94 shows `${comments.length} comments`. If the video has
fewer comments than requested (e.g. user asks 500, video has 30), `count` is 30
— correct. But there is no signal distinguishing "video only had 30" from
"fetch stopped early." With the H1 page-cap added, a 500-request that hits the
cap would show e.g. 230 with no indication it was truncated. Minor UX, but
relevant for the stated "AI analysis" use case where completeness matters.
Recommendation: when `count < requested AND nextPageToken existed`, return a
`truncated: true` flag and surface it.

### M3 — `_format_comment` drops deleted/empty-author distinction
`comments.py:38-45`. For a deleted account YouTube returns
`authorDisplayName` absent or empty. `_format_comment` stores `None` (no
`or ""`), and the frontend (`comments.js:52`, `:70`) renders
`comment.author || "Unknown"` — handled. But `text` for a removed comment can
be the literal string `""` *or* the snippet itself can be entirely absent
(thread with `topLevelComment` missing). `comments.py:98`
`thread.get("topLevelComment", {}).get("snippet", {})` defends against that and
produces an all-empty entry — which still gets appended and counted (line 105).
Result: empty ghost comments inflate `count` and show as
"`N. Unknown`" with blank text. Recommendation: skip entries where both
`author` and `text` are empty.

### M4 — File-size / structure: fine, but `comments.py` mixes 2 regexes already in `parsers.py`
`comments.py:14-16` defines `_VIDEO_ID_RE` and `_PATH_ID_RE`. The `/shorts/`,
`/live/`, `/embed/` handling overlaps conceptually with
`parsers.parse_input_target` which already routes URL segments. Not DRY: there
are now two URL-parsing code paths. `parsers.py` does **not** currently handle
`/shorts/` for video IDs, so the new regex is needed — but the cleaner fix is to
extend `extract_video_id_from_url` (or `parse_input_target`) in `parsers.py` so
all video-ID extraction lives in one module. All files are under 200 lines, so
no hard violation, just a DRY note.

---

## Low

### L1 — `copyToClipboard` fallback: `execCommand` is deprecated but correct
`comments.js:131-145`. The fallback creates a `textarea`, selects, calls
`document.execCommand("copy")`. Logic is correct and the `textarea` is removed
in all paths (success and the inner `catch`). One nit: the fallback textarea is
visible-but-offscreen-by-default for a frame — it has no inline styles to hide
it (`position:absolute; left:-9999px`), so on slow renders it can briefly flash
and can scroll the page on `.select()`. Add
`area.style.position = "fixed"; area.style.opacity = "0";` before append.
Functionally fine; cosmetic.

### L2 — `formatDate` returns the raw value on parse failure
`comments.js:24` `if (Number.isNaN(date.getTime())) return value;`. If the API
ever returns a non-ISO date, the raw string is shown. Harmless (still goes
through `textContent`), but inconsistent with the "clean text" goal. Minor.

### L3 — No client-side `max` validation; relies entirely on server clamp
`comments.js:161` sends `countSelect.value` (always 50/100/200/500 from the
`<select>`). Safe today. But `/api/comments` is directly reachable —
`?max=99999` is clamped server-side by `comments.py:75`
`max(1, min(max_results, MAX_COMMENTS))` — good, the clamp is the real defense.
No action needed; noting the defense-in-depth is correct here.

### L4 — `order` param case handling
`app.py:77` lowercases `order`; `comments.py:76` whitelists it. Double-guarded,
correct. No issue.

### L5 — Enter-key handler has no debounce
`comments.js:180-182` — pressing Enter repeatedly fires `fetchComments` each
time. `fetchBtn.disabled` is set inside `fetchComments` (line 156) so a second
Enter while in-flight still calls the function; it proceeds past the disabled
check (the guard is only `if (!url)`). Each call re-issues the fetch. Minor
quota/UX waste. Recommendation: early-return if `fetchBtn.disabled` is already
true at the top of `fetchComments`.

---

## Security Review Summary (per focus areas)

- **XSS**: PASS. Every API-derived string (`author`, `text`, `publishedAt`,
  `likes`) is assigned via `textContent` (`comments.js:18,40,52,58,70,75,85,94`).
  The only two `innerHTML` uses (`comments.js:92`, `:96`) write a constant
  empty string and a constant literal `<p class="muted">No comments found.</p>`
  — no interpolation, safe.
- **Copy export**: PASS. `buildPlainText` produces a plain string; clipboard
  write does not touch the DOM as HTML.
- **Error leakage**: FAIL — see H2.
- **Input validation**: PASS — server-side clamp on `max`, whitelist on
  `order`, regex on video ID.

---

## Error Handling (comments-disabled / private / not-found)

- `commentsDisabled` → mapped (`comments.py:50`). PASS.
- `videoNotFound` → mapped (`comments.py:52`). PASS.
- Private/restricted → relies on substring `"HTTP 403"` (`comments.py:54`).
  Fragile: quota-exceeded is *also* HTTP 403 and would be mis-labeled
  "private or restricted." Recommendation: check for the specific reason token
  (`quotaExceeded`, `forbidden`) before the generic 403 branch.
- Missing `YOUTUBE_API_KEY` → `youtube_api.py:18` raises `RuntimeError`,
  surfaced verbatim to the client. Acceptable (no secret in message) but
  arguably should be a generic 500-class message.

---

## Test Coverage Gaps

`tests/test_comments.py` covers offline helpers only (23 tests pass). Missing:
- `fetch_comments` pagination logic (loop termination, page-cap) — not tested
  because it needs network. Recommend a test with a stubbed `api_get` (monkey-
  patch) to verify: loop stops at `max_results`, stops on null token, and the
  proposed `MAX_PAGES` cap.
- `resolve_video_id` with `?v=<11-junk-but-valid-charset>` and `/embed/`,
  `/live/` paths — `_PATH_ID_RE` is untested.
- `_format_comment` deleted-author / empty-snippet case (M3).

---

## Positive Observations

- Clean separation: fetch logic in `comments.py`, rendering in `comments.js`.
- `textContent`-only rendering — XSS-safe by construction.
- Server-side clamp on `max` and whitelist on `order` — correct trust boundary.
- `from None` exception chaining keeps tracebacks clean.
- Clipboard fallback removes the temp `textarea` in every path.
- `_format_comment` prefers `textOriginal` over `textDisplay` — correct for
  avoiding HTML entities in the AI-export text.

---

## Recommended Actions (priority order)

1. **H1** — add `MAX_PAGES` page cap to `fetch_comments` loop.
2. **H2** — make `_friendly_error` fail closed; log raw error server-side only.
3. **M3** — skip all-empty ghost comments before append/count.
4. **Error handling** — distinguish `quotaExceeded` from private-video 403.
5. **M2** — return a `truncated` flag when fetch stops short.
6. **Tests** — add stubbed-`api_get` pagination test + `_PATH_ID_RE` cases.
7. **L1/L5** — hide fallback textarea; early-return on in-flight fetch.

## Unresolved Questions

- Is `/api/comments` intended to be public, or gated behind the same "hidden"
  assumption as `/secret`? It is directly reachable and unauthenticated —
  affects how severe the H2 error leak is. The `/secret` page is "intentionally
  not linked" but that is security-by-obscurity; `/api/comments` has no guard
  at all.
- Expected behavior when a video has more comments than `MAX_COMMENTS` (500):
  silently cap, or tell the user? Currently silent.
