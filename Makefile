.PHONY: install run lint format build

install:
	uv sync

run:
	uv run python -m primitive_db.main

lint:
	uv run ruff check .

format:
	uv run ruff format .

build:
	uv build
