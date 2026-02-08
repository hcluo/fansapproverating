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

## Notes
- Ingestion is rate-limit-safe via central throttling and PRAW ratelimit config.
- Celery beat schedule:
  - Reddit ingest every 10 min
  - Aggregates nightly for yesterday + today
- Author names are hashed before storage.
- MVP uses regex boundary matching for aliases; can be swapped to trie/Aho-Corasick later.
