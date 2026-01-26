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
OPENROUTER_API_KEY=your_key_here
```

When `OPENROUTER_API_KEY` is provided, the API adds title/thumbnail trend analysis.

## Optional tuning (timeouts)

You can adjust timeouts via env:

```
HTTP_TIMEOUT=20
OPENROUTER_TIMEOUT=30
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

## Nginx sample

See `deployment/nginx/demo-youtube-data.emvn.co.conf`.
