"""Standalone real-API smoke test that does not require an MCP client."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .config import ConfigurationError, Settings
from .git_service import GitService, GitServiceError
from .hy3_client import Hy3Client, Hy3ClientError
from .review_service import ReviewService

_BUILTIN_DIFF = """diff --git a/app/users.py b/app/users.py
index a5d42ab..c3e8517 100644
--- a/app/users.py
+++ b/app/users.py
@@ -8,4 +8,4 @@ def find_user(connection, username: str):
-    return connection.execute("SELECT id FROM users WHERE username = ?", (username,))
+    return connection.execute(f"SELECT id FROM users WHERE username = '{username}'")
"""


def load_diff(diff_file: str | None, workspace_root: Path) -> str:
    """Load an optional diff file while enforcing the configured workspace boundary."""
    if diff_file is None:
        return _BUILTIN_DIFF

    path = Path(diff_file).expanduser()
    if not path.is_absolute():
        path = workspace_root / path
    path = path.resolve()
    if not path.is_relative_to(workspace_root):
        raise GitServiceError("diff file must stay inside HY3_WORKSPACE_ROOT")
    if not path.is_file():
        raise GitServiceError(f"diff file does not exist: {path}")
    try:
        return path.read_text()
    except UnicodeDecodeError as exc:
        raise GitServiceError(f"diff file is not valid UTF-8 text: {path}") from exc


async def run_smoke_test(settings: Settings, diff: str) -> str:
    """Call the same review service used by MCP tools with a real Hy3 client."""
    service = ReviewService(
        GitService(settings.workspace_root, settings.max_diff_chars),
        Hy3Client(settings),
    )
    return await service.run(
        task="review",
        source="provided",
        provided_diff=diff,
        focus="security",
        language="Chinese",
        reasoning_effort="high",
    )


def main() -> None:
    """Validate configuration, call Hy3 once, and print the review result."""
    parser = argparse.ArgumentParser(
        prog="hy3-code-review-smoke-test",
        description=(
            "Call the configured Hy3 API once with a small security-review diff. "
            "This may consume API quota."
        ),
    )
    parser.add_argument(
        "--diff-file",
        help=(
            "optional UTF-8 unified diff inside HY3_WORKSPACE_ROOT; "
            "uses a built-in demo otherwise"
        ),
    )
    args = parser.parse_args()

    try:
        settings = Settings.from_env()
        diff = load_diff(args.diff_file, settings.workspace_root)
        result = asyncio.run(run_smoke_test(settings, diff))
    except (ConfigurationError, GitServiceError, Hy3ClientError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    print(result)


if __name__ == "__main__":
    main()
