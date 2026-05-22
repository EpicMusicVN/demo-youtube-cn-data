# EMVN YouTube Channel Inspector

Web UI + API for inspecting YouTube channels using YouTube Data API.

## Local run

```
python3 -m pip install -r requirements.txt
YOUTUBE_API_KEY=your_key_here python3 app.py
```

Open http://localhost:8080

## Docker

```
docker compose up -d --build
```

The container binds `8081:8080` by default. Adjust `docker-compose.yml` if needed.

## Environment

Create `.env` with:

```
YOUTUBE_API_KEY=your_key_here
VERTEX_API_KEY=your_key_here
```

When `VERTEX_API_KEY` is provided, the API adds title/thumbnail trend analysis.

Vertex model configuration (optional):

```
VERTEX_MODEL=gemini-3-flash-preview
VERTEX_API_BASE=https://generativelanguage.googleapis.com/v1beta
VERTEX_PROJECT_ID=your_gcp_project   # if calling Vertex AI endpoints
VERTEX_LOCATION=us-central1
```

## Optional tuning (timeouts)

You can adjust timeouts via env:

```
HTTP_TIMEOUT=20
VERTEX_TIMEOUT=30
ANALYSIS_BUDGET_SECONDS=20
ANALYSIS_THUMBNAILS_MAX=6
ANALYSIS_THUMBNAILS_PER_GROUP=10
```

To skip analysis per request: `/api/inspect?url=...&analysis=0`

## Long vs Short splits

The API now returns `topViewedLong`, `topViewedShort`, `latestLong`, `latestShort`.
You can control list sizes with:

```
VIDEO_FETCH_MAX=50
VIDEO_OUTPUT_MAX=10
```

Thumbnail analysis:
- Default samples 10 thumbnails from Top Viewed and 10 from Latest.
- Set `ANALYSIS_THUMBNAILS_PER_GROUP` to change this; or set `ANALYSIS_THUMBNAILS_MAX` to control total.

Shorts detection:
- `SHORT_MAX_SECONDS` defines short vs long (default 240 seconds) when UUSH is unavailable.
- `USE_UUSH_PLAYLIST` defaults to `1` and uses `UUSH` to classify Shorts when available.
- `latestShort` uses UUSH when available; otherwise duration-based split on uploads.
- `topViewedShort` uses `videoDuration=short` when allowed and intersects with UUSH when available; otherwise duration-based.

## Secret competitor page

A hidden competitor-analysis page is served at `/secret`. It is intentionally
**not linked** from anywhere, and is gated by an access code: visitors must
enter the code (env `SECRET_ACCESS_CODE`) before the page — or its
`/api/inspect?lean=1` endpoint — will respond. Set `SECRET_ACCESS_CODE` and
`FLASK_SECRET_KEY` in `.env` for production.

It clones the inspect feature (paste channel link → analyse) but drops the
Top Viewed / Latest video grids. Instead it surfaces derived competitor
metrics from the latest ~50 uploads: upload cadence & timing (KST), content
format (shorts ratio, duration trend, title formulas), engagement (like /
comment / engagement rates, breakout & underperforming videos) and SEO
intelligence (top tags, sponsor rate, revenue streams, paid placements).

When `VERTEX_API_KEY` is set it also adds an AI section: structured
thumbnail-design breakdown (characters, colours, art style, typography,
branding), "how to compete" strategy tips, and recommended tags for a new
channel — all grounded in the computed metrics.

It calls `/api/inspect?lean=1`, which skips the costly top-viewed `/search`
calls — roughly 11 quota units per channel. The same `competitorAnalysis`
block is also included in the normal `/api/inspect` response.

## Comment fetcher page

A comment fetcher is served at `/comments`, reachable via a button on the
`/secret` page. It is gated by the same access code as `/secret` — the page
and its `/api/comments` endpoint stay locked until the code is entered.
Paste a video URL (or ID / Shorts link), pick how many comments to fetch
(50–500) and a sort order, then read the thread in a fixed-height scrollable
view or copy it as clean plain text for AI analysis.

Top-level comments are returned with their inline replies (the API includes
up to ~5 per thread; remaining replies are shown as a "+N more" note). The
endpoint is `/api/comments?url=...&max=...&order=relevance|time` and costs
1 quota unit per 100 comments.

## Nginx sample

See `deployment/nginx/demo-youtube-data.emvn.co.conf`.
