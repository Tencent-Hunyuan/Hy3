.PHONY: test lint fmt typecheck eval

test:
	uv run pytest

lint:
	uv run ruff check . && uv run ruff format --check .

fmt:
	uv run ruff format .

typecheck:
	uv run ty check

eval:
	uv run python -m eval
