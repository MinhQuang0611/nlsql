.PHONY: help up down db-up db-down seed migrate test-db shell logs

# ── Variables ─────────────────────────────────────────────────────────────────
COMPOSE = docker compose
PYTHON  = python

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Infrastructure ────────────────────────────────────────────────────────────
db-up:         ## Start PostgreSQL only
	$(COMPOSE) up -d postgres

db-down:       ## Stop PostgreSQL
	$(COMPOSE) stop postgres

up:            ## Start all services (app + db)
	$(COMPOSE) --profile app up -d

down:          ## Stop all services
	$(COMPOSE) down

tools-up:      ## Start pgAdmin (browser: http://localhost:5050)
	$(COMPOSE) --profile tools up -d pgadmin

logs:          ## Tail docker logs
	$(COMPOSE) logs -f

# ── Database ──────────────────────────────────────────────────────────────────
seed:          ## Run seed.sql against running DB
	docker exec -i nlsql_db \
	  psql -U $${DB_USER:-postgres} -d $${DB_NAME:-nlsql} \
	  < db/seeds/seed.sql

migrate:       ## Run Alembic migrations
	alembic upgrade head

migrate-gen:   ## Autogenerate new migration (MSG=<description>)
	alembic revision --autogenerate -m "$(MSG)"

test-db:       ## Test DB connection
	$(PYTHON) scripts/test_db_connection.py

# ── Dev ───────────────────────────────────────────────────────────────────────
install:       ## Install Python dependencies
	pip install -r requirements.txt

run:           ## Run FastAPI dev server
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:          ## Run pytest
	pytest -v