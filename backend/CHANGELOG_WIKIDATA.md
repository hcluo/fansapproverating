# Wikidata Player Directory Changes

## What changed
- Added Wikidata snapshot fetcher and normalization utilities.
- Added snapshot upsert seeding with idempotent alias insertion.
- Added `wikidata_qid` column + indexes for player lookup.
- Added optional monthly refresh task + admin endpoints.

## Where to look
- Snapshot fetch: `backend/scripts/fetch_wikidata_players.py`
- SPARQL + client: `backend/app/services/wikidata/queries.py`, `backend/app/services/wikidata/client.py`
- Normalization + denylist: `backend/app/services/wikidata/normalize.py`, `backend/data/alias_denylist.txt`
- Seeding: `backend/app/scripts/seed_wikidata_players.py`, `backend/app/services/wikidata/seed.py`
- Refresh task + schedule: `backend/app/tasks/jobs.py`, `backend/app/celery_app.py`
- Admin endpoints: `backend/app/api/routes.py`
- Migration: `backend/alembic/versions/0002_wikidata_qid.py`
