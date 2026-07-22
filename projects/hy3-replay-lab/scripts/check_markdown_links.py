from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK = re.compile(r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
SKIP_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-cache",
    ".venv",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
}


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in SKIP_DIRECTORIES for part in path.relative_to(root).parts)
    )


def local_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.removeprefix("<").removesuffix(">")
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return None
    relative_path = unquote(parsed.path)
    if not relative_path:
        return None
    return (source.parent / relative_path).resolve()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures: list[str] = []
    checked = 0
    for source in markdown_files(root):
        content = source.read_text(encoding="utf-8")
        for match in LINK.finditer(content):
            target = local_target(source, match.group("target"))
            if target is None:
                continue
            checked += 1
            if not target.exists():
                failures.append(
                    f"{source.relative_to(root)}: missing {match.group('target')}"
                )
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"checked {checked} local Markdown targets across {len(markdown_files(root))} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
