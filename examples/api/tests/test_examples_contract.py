from __future__ import annotations

import ast
import re
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
STEMS = (
    "01_basic_chat",
    "02_streaming",
    "03_latency_comparison",
    "04_tool_calling",
    "05_reasoning_modes",
    "06_error_handling_retry",
)


def test_every_example_has_script_and_walkthrough() -> None:
    for stem in STEMS:
        assert (API_DIR / f"{stem}.py").is_file()
        assert (API_DIR / f"{stem}.md").is_file()


def test_all_example_python_files_parse() -> None:
    for path in sorted(API_DIR.rglob("*.py")):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_walkthroughs_cover_request_parsing_and_output() -> None:
    for stem in STEMS:
        text = (API_DIR / f"{stem}.md").read_text(encoding="utf-8").lower()
        assert "request" in text
        assert "response" in text
        assert "example output" in text
        assert "```" in text


def test_local_markdown_links_resolve() -> None:
    markdown_files = [REPO_ROOT / "quickstart.md", API_DIR / "README.md"]
    markdown_files.extend(API_DIR / f"{stem}.md" for stem in STEMS)
    link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")

    for markdown_file in markdown_files:
        for target in link_pattern.findall(markdown_file.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            path_part = target.split("#", 1)[0]
            resolved = (markdown_file.parent / path_part).resolve()
            assert resolved.exists(), f"broken link in {markdown_file}: {target}"


def test_tracked_content_has_no_key_shaped_secret() -> None:
    key_pattern = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")
    paths = [REPO_ROOT / "quickstart.md"]
    paths.extend(API_DIR.rglob("*"))
    for path in paths:
        if not path.is_file() or path.suffix not in {".md", ".py", ".example"}:
            continue
        assert not key_pattern.search(path.read_text(encoding="utf-8")), path
