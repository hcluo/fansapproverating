up:
	docker compose up --build

down:
	docker compose down

backend-migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m app.scripts.seed_players

test:
	docker compose run --rm backend pytest -q
