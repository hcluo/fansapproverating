up:
	docker compose up --build

down:
	docker compose down

backend-migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m app.scripts.seed_wikidata_players

players-snapshot:
	docker compose run --rm backend python scripts/fetch_wikidata_players.py

seed-players:
	docker compose run --rm backend python -m app.scripts.seed_wikidata_players

test:
	docker compose run --rm backend pytest -q
