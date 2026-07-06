# Priya Voice Agent — developer shortcuts
.PHONY: help install dev-db init-db migrate revision run-agent run-api setup-sip \
        bench-llm bench-tts bench-e2e test lint fmt docker-up docker-down docker-logs

help:
	@echo "Targets:"
	@echo "  install     Install deps + dev extras (editable)"
	@echo "  dev-db      Start a local Postgres via docker"
	@echo "  init-db     Create tables (dev bootstrap)"
	@echo "  migrate     Run alembic upgrade head"
	@echo "  revision    Autogenerate a migration (m='msg')"
	@echo "  run-agent   Run the LiveKit agent worker"
	@echo "  run-api     Run the FastAPI control plane"
	@echo "  setup-sip   Provision Vobiz SIP trunks + dispatch rule"
	@echo "  bench-*     Latency benchmarks (llm/tts/e2e)"
	@echo "  test/lint/fmt  Quality gates"
	@echo "  docker-*    Compose up/down/logs"

install:
	pip install -e ".[dev]"

dev-db:
	docker run -d --name priya-pg -e POSTGRES_DB=priya -e POSTGRES_USER=priya \
		-e POSTGRES_PASSWORD=priya -p 5432:5432 postgres:16-alpine

init-db:
	python scripts/init_db.py

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(m)"

run-agent:
	python -m priya.agent.worker dev

run-api:
	uvicorn priya.api.main:app --reload --host 0.0.0.0 --port 8080

setup-sip:
	python scripts/setup_sip.py

bench-llm:
	python scripts/benchmark_llm.py --runs 10

bench-tts:
	python scripts/benchmark_tts.py --runs 10

bench-e2e:
	python scripts/benchmark_e2e.py --runs 10

test:
	pytest -q

lint:
	ruff check src tests
	mypy src

fmt:
	ruff format src tests scripts
	ruff check --fix src tests

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f agent api
