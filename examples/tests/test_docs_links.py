"""Lightweight checks that docs and inventory stay consistent."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

EXAMPLES = [
    "01_basic_chat",
    "02_streaming",
    "03_nonstream_vs_stream",
    "04_tool_calling",
    "05_reasoning_mode",
    "06_error_handling_retry",
]


def test_required_files_exist():
    assert (REPO / "quickstart.md").is_file()
    assert (REPO / "quickstart_CN.md").is_file()
    assert (ROOT / "common.py").is_file()
    assert (ROOT / "requirements.txt").is_file()
    assert (ROOT / "requirements-dev.txt").is_file()
    assert (ROOT / ".env.example").is_file()
    assert (ROOT / "README.md").is_file()
    assert (ROOT / "tests" / "test_common.py").is_file()
    assert (ROOT / "tests" / "test_live_smoke.py").is_file()

    for lang in ("en", "cn"):
        assert (ROOT / lang / "README.md").is_file()
        for name in EXAMPLES:
            assert (ROOT / lang / f"{name}.py").is_file()
            assert (ROOT / lang / f"{name}.md").is_file()
            assert (ROOT / lang / f"{name}.ipynb").is_file()


def test_quickstart_covers_issue_sections():
    text = (REPO / "quickstart.md").read_text(encoding="utf-8").lower()
    for needle in (
        "base url",
        "api key",
        "model",
        "rate",
        "temperature",
        "top_p",
        "max_tokens",
        "stop",
        "tools",
        "reasoning",
        "curl",
        "openai",
        "troubleshoot",
        "tokenhub",
    ):
        assert needle in text, f"quickstart.md missing section topic: {needle}"


def test_quickstart_cn_covers_issue_sections():
    text = (REPO / "quickstart_CN.md").read_text(encoding="utf-8")
    for needle in (
        "Base URL",
        "API Key",
        "temperature",
        "top_p",
        "max_tokens",
        "tools",
        "思考",
        "curl",
        "TokenHub",
        "排查",
    ):
        assert needle in text, f"quickstart_CN.md missing: {needle}"


def test_no_hardcoded_secrets_in_examples():
    patterns = ("sk-live", "sk-proj-", "Bearer sk-")
    for path in ROOT.rglob("*"):
        if path.suffix not in {".py", ".md", ".ipynb", ".txt", ".example"}:
            continue
        if "__pycache__" in path.parts or path.name == "test_docs_links.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for p in patterns:
            assert p not in text, f"possible secret pattern {p!r} in {path}"
