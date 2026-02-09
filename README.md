# FansApprove Rating MVP

Monorepo with:
- `backend/`: FastAPI + Celery + PostgreSQL + Redis + PRAW + VADER
- `frontend/`: Next.js app

## Features
- Reddit ingestion from configured subreddits (`reddit_ingest_task`)
- Alias-based NBA player mention extraction with denylist support
- VADER sentiment per comment/player mention
- Daily player aggregate metrics with weighted sentiment (upvotes capped)
- Frontend list/detail pages with sentiment chart placeholder narratives
- Wikidata-backed player directory snapshots (CC0) with idempotent upsert

## Repo inspection notes (Feb 8, 2026)
- Player seed data currently lives in `backend/data/players_seed.json`.
- Legacy seeding uses `backend/app/scripts/seed_players.py` and was wired to `make seed`.
- Player schema + aliases are defined in `backend/app/models/entities.py` and `backend/alembic/versions/0001_initial.py`.
- Alias usage flows through `backend/app/services/matcher.py` and Celery ingest in `backend/app/tasks/jobs.py`.
- Player APIs are in `backend/app/api/routes.py` (`/players`, `/players/{id}`, metrics, narratives).

## Prerequisites
- Docker + Docker Compose

## Setup
1. Copy env file:
   ```bash
   cp .env.example .env
   ```
2. Create Reddit API credentials:
   - Go to https://www.reddit.com/prefs/apps
   - Create a "script" app
   - Put values into `.env`:
     - `REDDIT_CLIENT_ID`
     - `REDDIT_CLIENT_SECRET`
     - `REDDIT_USER_AGENT` (include app + your username)

3. Start stack:
   ```bash
   make up
   ```

4. Run database migrations:
   ```bash
   make backend-migrate
   ```

5. Seed sample players:
   ```bash
   make seed
   ```

6. Trigger manual ingestion:
   ```bash
   curl -X POST http://localhost:8000/admin/ingest/reddit
   ```

7. Trigger recompute:
   ```bash
   curl -X POST http://localhost:8000/admin/recompute
   ```

8. Open UI:
   - Frontend: http://localhost:3000
   - Backend docs: http://localhost:8000/docs

## API endpoints
- `GET /health`
- `GET /players?query=`
- `GET /players/{player_id}`
- `GET /players/{player_id}/metrics?from=YYYY-MM-DD&to=YYYY-MM-DD`
- `GET /players/{player_id}/narratives?date=YYYY-MM-DD`
- `POST /admin/ingest/reddit`
- `POST /admin/recompute`
- `POST /admin/players/refresh-wikidata` (requires `X-Admin-Token` if `ADMIN_TOKEN` is set)
- `GET /admin/players/source-status` (requires `X-Admin-Token` if `ADMIN_TOKEN` is set)

## Wikidata player directory (CC0)
Wikidata is used as an open (CC0) player directory. The workflow is:
1. Fetch snapshot from Wikidata:
   ```bash
   make players-snapshot
   ```
2. Upsert snapshot into Postgres:
   ```bash
   make seed-players
   ```
3. `make seed` now runs `seed-players` and falls back to `players_seed.json` if no snapshot exists.

Snapshot details:
- Stored at `backend/data/wikidata_players_snapshot.json`
- Snapshot generation script: `backend/scripts/fetch_wikidata_players.py`
- Alias denylist: `backend/data/alias_denylist.txt`

Troubleshooting:
- SPARQL timeouts: rerun with smaller batches (e.g. `python scripts/fetch_wikidata_players.py --limit 200 --max-rows 2000`).
- If Wikidata is slow, the snapshot script sleeps between batches (`--sleep`).

Environment variables:
- `ADMIN_TOKEN` for admin endpoints (via `X-Admin-Token` header).
- `ENABLE_WIKIDATA_REFRESH=true` to enable monthly refresh via Celery beat.

## Notes
- Ingestion is rate-limit-safe via central throttling and PRAW ratelimit config.
- Celery beat schedule:
  - Reddit ingest every 10 min
  - Aggregates nightly for yesterday + today
  - Optional monthly Wikidata refresh (enabled via `ENABLE_WIKIDATA_REFRESH=true`)
- Author names are hashed before storage.
- MVP uses regex boundary matching for aliases; can be swapped to trie/Aho-Corasick later.
