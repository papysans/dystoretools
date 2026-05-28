.PHONY: up down logs ps migrate migrate-create migrate-down api-dev web-dev lint typecheck test fmt install playwright-install

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

migrate:
	docker compose exec api alembic upgrade head

migrate-create:
	@read -p "Revision message: " msg; \
	docker compose exec api alembic revision --autogenerate -m "$$msg"

migrate-down:
	docker compose exec api alembic downgrade -1

api-dev:
	cd backend && uvicorn dystore.main:app --host 0.0.0.0 --port 8080 --reload

web-dev:
	cd web && pnpm dev

install:
	cd backend && pip install -e ".[dev]"
	cd web && pnpm install

playwright-install:
	cd backend && python -m playwright install chrome

lint:
	cd backend && ruff check . && ruff format --check .
	cd web && pnpm lint

typecheck:
	cd backend && mypy dystore
	cd web && pnpm typecheck

test:
	cd backend && pytest -q
	cd web && pnpm test --run

fmt:
	cd backend && ruff format . && ruff check --fix .
	cd web && pnpm fmt
