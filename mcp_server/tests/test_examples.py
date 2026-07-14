import json
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parents[1] / "examples"


@pytest.mark.parametrize("filename", ["cursor.mcp.json", "codebuddy.mcp.json"])
def test_client_config_is_valid_and_secret_free(filename: str) -> None:
    config = json.loads((EXAMPLES / filename).read_text())

    server = config["mcpServers"]["hy3-code-review"]
    assert server["command"].endswith(
        "/mcp_server/.venv/bin/hy3-code-review-mcp"
    )
    assert server["env"]["HY3_ENV_FILE"].endswith("/mcp_server/.env")
    assert server["env"]["HY3_WORKSPACE_ROOT"] == "/absolute/path/to/Hy3"
    assert "HY3_API_KEY" not in server["env"]


def test_demo_diff_contains_no_secret_placeholders() -> None:
    demo = (EXAMPLES / "demo-security-bug.diff").read_text()

    assert "diff --git" in demo
    assert "API_KEY" not in demo
    assert "PRIVATE KEY" not in demo


def test_delivery_gitignore_protects_local_environment() -> None:
    project_root = Path(__file__).parents[1]
    ignored = (project_root / ".gitignore").read_text().splitlines()

    assert ".env" in ignored
    assert ".venv/" in ignored
    assert "dist/" in ignored
