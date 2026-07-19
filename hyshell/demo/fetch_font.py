# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Fetch the CJK mono font needed only for *recording* the demo GIFs.

The font (Noto Sans Mono CJK SC, ~16 MB) is cached under
``~/.cache/hyshell-fonts/`` and is **never** committed to the repository.
Users who just watch the shipped GIFs or run hyshell itself do not need it.
"""

from __future__ import annotations

import sys
from pathlib import Path

FONT_URL = (
    "https://github.com/googlefonts/noto-cjk/raw/main/Sans/Mono/"
    "NotoSansMonoCJKsc-Regular.otf"
)
CACHE_DIR = Path.home() / ".cache" / "hyshell-fonts"
FONT_PATH = CACHE_DIR / "NotoSansMonoCJKsc-Regular.otf"
_MIN_BYTES = 1_000_000  # sanity floor: a real OTF is ~16 MB


def ensure_font(quiet: bool = False) -> Path | None:
    """Return the cached font path, downloading it on first use."""
    if FONT_PATH.exists() and FONT_PATH.stat().st_size > _MIN_BYTES:
        return FONT_PATH
    try:
        import httpx

        if not quiet:
            print(f"downloading CJK font → {FONT_PATH} …")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = FONT_PATH.with_suffix(".part")
        with httpx.stream("GET", FONT_URL, follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with tmp_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        if tmp_path.stat().st_size < _MIN_BYTES:
            tmp_path.unlink(missing_ok=True)
            return None
        tmp_path.rename(FONT_PATH)
        return FONT_PATH
    except Exception as exc:  # noqa: BLE001 - best-effort helper
        if not quiet:
            print(f"font download failed: {exc}", file=sys.stderr)
        return None


if __name__ == "__main__":
    path = ensure_font()
    if path is None:
        print("无法获取 CJK 字体(录制 GIF 需要;运行 hyshell 本身不需要)。", file=sys.stderr)
        sys.exit(1)
    print(path)
