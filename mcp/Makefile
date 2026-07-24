# Hy3 Deep Research MCP Server — development tasks
# Usage: make <target>

.PHONY: install dev test test-cov demo inspector clean

# Install in editable mode with dev dependencies
install:
	pip install -e ".[dev]"

# Install with uv (faster)
dev:
	uv pip install -e ".[dev]"

# Run all tests
test:
	pytest -v

# Run tests with coverage
test-cov:
	pytest --cov=hy3_deep_research --cov-report=term-missing -v

# Run the demo client (requires HUNYUAN_API_KEY)
demo:
	python demo/demo_mcp_client.py

# Run the demo with a custom query
demo-query:
	python demo/demo_mcp_client.py --query "$(QUERY)"

# Launch MCP Inspector for interactive testing
inspector:
	npx @modelcontextprotocol/inspector python -m hy3_deep_research

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -f .coverage
