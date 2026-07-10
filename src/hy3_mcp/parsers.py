"""File parsers for the knowledge base.

Per the contest scope this server supports plain-text formats only:
``.txt``, ``.md`` and ``.csv`` (zero extra dependencies). A clear error is
raised for unsupported extensions so the user knows to enable the optional
``pdf`` / ``docx`` extras if they need them.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass


SUPPORTED_EXTENSIONS = (".txt", ".md", ".markdown", ".csv")


class UnsupportedFileType(Exception):
    """Raised when a file has an extension outside the supported set."""


@dataclass
class ParsedDocument:
    """A parsed document: its source path and full text content."""

    path: str
    content: str


def parse_file(path: str) -> ParsedDocument:
    """Parse a single file into a :class:`ParsedDocument`.

    Raises:
        FileNotFoundError: if the path does not exist.
        UnsupportedFileType: if the extension is not supported.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(
            f"Unsupported file type '{ext}' for {path}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    if ext == ".csv":
        content = _parse_csv(path)
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()

    return ParsedDocument(path=path, content=content)


def _parse_csv(path: str) -> str:
    """Flatten a CSV file into a readable text block."""
    rows: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        for i, row in enumerate(reader):
            rows.append(f"[row {i}] " + " | ".join(cell.strip() for cell in row))
    return "\n".join(rows)


def iter_supported_paths(paths: list[str]) -> list[str]:
    """Expand a list of file/directory paths into a flat list of supported files.

    Directories are walked recursively; unsupported files inside a directory
    are silently skipped (so a mixed folder still loads the usable parts).
    """
    resolved: list[str] = []
    for raw in paths:
        if os.path.isdir(raw):
            for root, _dirs, files in os.walk(raw):
                for name in sorted(files):
                    if os.path.splitext(name)[1].lower() in SUPPORTED_EXTENSIONS:
                        resolved.append(os.path.join(root, name))
        elif os.path.isfile(raw):
            ext = os.path.splitext(raw)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                resolved.append(raw)
            # Explicitly-listed unsupported files are left to parse_file() to
            # report clearly when the user asks to load them directly.
        else:
            # Non-existent explicit path: let parse_file raise later, but skip
            # here for directory-expanded lists.
            resolved.append(raw)
    return resolved
