# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Record the scripted demo flows and render them into the shipped GIFs.

Usage (from the ``hyshell/`` project directory)::

    python demo/record_gifs.py --flow all                 # offline fake backend
    HY3_API_KEY=... python demo/record_gifs.py --flow all --backend real

Offline recordings are byte-deterministic. Real-backend recordings differ run
to run (the model is sampled at temperature 0.9) and the scripted inputs may
diverge from real model output — the flow then ends early, which is expected.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (str(ROOT / "src"), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from rich.console import Console  # noqa: E402

from ansi2gif import FrameRenderer, assemble_gif  # noqa: E402
from fetch_font import ensure_font  # noqa: E402
from hyshell.config import BackendMode, Settings  # noqa: E402
from hyshell.demo_flows import FLOWS, run_flow  # noqa: E402

GIF_NAMES = {"daily": "demo-1-daily.gif", "guard_fix": "demo-2-guard-fix.gif"}
ROWS = 34
FIRST_FRAME_MS = 3800
LAST_FRAME_MS = 6000
DEFAULT_FRAME_MS = 2800
MAX_TOTAL_MS = 120_000  # issue requirement: <= 2 minutes
MAX_BYTES = 2 * 1024 * 1024


def record_flow(name: str, backend: str, out_dir: Path, renderer: FrameRenderer) -> Path:
    console = Console(
        record=True,
        force_terminal=True,
        width=80,
        color_system="truecolor",
        file=io.StringIO(),
    )
    accumulated = ""
    frames: list[str] = []

    def hook() -> None:
        nonlocal accumulated
        block = console.export_text(styles=True, clear=True)
        if block:
            accumulated += block
        visible = "\n".join(accumulated.split("\n")[-ROWS:])
        if not frames or visible != frames[-1]:
            frames.append(visible)

    if backend == "real":
        settings = Settings.from_env()
        if settings.mode is BackendMode.FAKE:
            raise SystemExit("--backend real 需要设置 HY3_API_KEY")
    else:
        settings = Settings.from_env({}, offline=True)

    tmp_root = Path(tempfile.mkdtemp(prefix="hyshell-gif-"))
    try:
        settings = replace(settings, home_dir=tmp_root / "home")
        run_flow(
            name,
            console=console,
            workdir=tmp_root / "workspace",
            settings=settings,
            frame_hook=hook,
        )
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    durations = [DEFAULT_FRAME_MS] * len(frames)
    durations[0] = FIRST_FRAME_MS
    durations[-1] = LAST_FRAME_MS
    total_ms = sum(durations)
    if total_ms > MAX_TOTAL_MS:
        scale = MAX_TOTAL_MS / total_ms
        durations = [max(800, int(d * scale)) for d in durations]

    images = [renderer.render(frame) for frame in frames]
    out_path = out_dir / GIF_NAMES.get(name, f"demo-{name}.gif")
    assemble_gif(images, durations, out_path)
    size = out_path.stat().st_size
    print(
        f"{out_path.name}: {len(frames)} frames, {sum(durations) / 1000:.1f}s playtime, "
        f"{size / 1024:.0f} KB"
    )
    if size > MAX_BYTES:
        print(f"WARNING: {out_path.name} exceeds 2MB", file=sys.stderr)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record hyshell demo GIFs")
    parser.add_argument("--flow", default="all", choices=[*FLOWS, "all"])
    parser.add_argument("--backend", default="fake", choices=["fake", "real"])
    parser.add_argument("--out", default=str(ROOT / "assets"), help="output directory")
    args = parser.parse_args()

    font = ensure_font()
    if font is None:
        print(
            "错误:缺少 CJK 字体且下载失败——GIF 含大量中文,拒绝渲染豆腐块。\n"
            "请先手动运行 python demo/fetch_font.py(仅录制需要此字体)。",
            file=sys.stderr,
        )
        return 3

    renderer = FrameRenderer(cjk_font_path=font, rows=ROWS)
    out_dir = Path(args.out)
    names = list(FLOWS) if args.flow == "all" else [args.flow]
    for name in names:
        record_flow(name, args.backend, out_dir, renderer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
