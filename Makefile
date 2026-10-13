.PHONY: up down logs test lint benchmark reset

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	docker build --target test -t support-operations-agent-test .
	docker run --rm support-operations-agent-test python -m pytest -q

lint:
	docker build --target test -t support-operations-agent-test .
	docker run --rm support-operations-agent-test ruff check .

benchmark:
	python -m eval.run --base-url http://localhost:8000 --dataset eval/cases.jsonl

reset:
	docker compose down -v
