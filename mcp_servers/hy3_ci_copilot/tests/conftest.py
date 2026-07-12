from __future__ import annotations

from pathlib import Path

import pytest

from hy3_ci_copilot.config import Settings


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        """name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (tmp_path / "failed.log").write_text(
        "setup complete\nERROR: tests/test_api.py::test_health failed\n1 failed\n",
        encoding="utf-8",
    )
    (tmp_path / "successful.log").write_text(
        "setup complete\ntests/test_api.py::test_health passed\n1 passed\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def settings(repository: Path) -> Settings:
    return Settings(
        api_key="test-key-not-secret",
        base_url="https://hy3.example.test/v1",
        model="hy3",
        api_style="native",
        allowed_roots=(repository,),
        timeout_seconds=5,
        max_input_chars=20_000,
        max_output_tokens=512,
        max_retries=0,
    )
