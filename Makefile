.PHONY: dev test lint fmt precommit hooks

dev:
	uv run fastapi dev backend/app/main.py

test:
	uv run pytest -q

lint:
	ruff check backend

fmt:
	ruff format backend

precommit:
	pre-commit run --all-files

hooks:
	pre-commit install
