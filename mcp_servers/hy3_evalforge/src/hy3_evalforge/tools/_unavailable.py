"""Temporary phase-one responses until each workflow service is wired in."""

from __future__ import annotations


def unavailable(tool_name: str) -> dict[str, object]:
    """Return a structured, non-sensitive status instead of an unhandled server exception."""
    return {
        "error": {
            "code": "INPUT_ERROR",
            "message": (
                f"{tool_name} is not available until its workflow implementation is installed."
            ),
        }
    }
