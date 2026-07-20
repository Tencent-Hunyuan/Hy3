"""Fail when a local Markdown link points to a missing path."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:")


def check_file(markdown: Path) -> list[str]:
    failures: list[str] = []
    text = markdown.read_text(encoding="utf-8")
    for match in LINK.finditer(text):
        destination = match.group(1).strip().strip("<>")
        if not destination or destination.startswith("#"):
            continue
        if destination.lower().startswith(EXTERNAL_SCHEMES):
            continue
        destination = unquote(destination.split("#", maxsplit=1)[0])
        target = (markdown.parent / destination).resolve()
        if not target.exists():
            line = text.count("\n", 0, match.start()) + 1
            failures.append(f"{markdown}:{line}: missing local link: {destination}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    arguments = parser.parse_args()
    failures = [failure for path in arguments.paths for failure in check_file(path)]
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Checked {len(arguments.paths)} Markdown files; all local links resolve.")


if __name__ == "__main__":
    main()
