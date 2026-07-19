# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""ANSI→GIF pipeline: SGR parsing, cell layout, rendering, shipped assets."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PIL", reason="pillow 未安装(dev/demo extra)— 跳过 GIF 管线测试,核心套件不受影响")

from PIL import Image  # noqa: E402

from demo.ansi2gif import (  # noqa: E402
    BACKGROUND,
    FrameRenderer,
    Style,
    apply_sgr,
    assemble_gif,
    parse_ansi_lines,
    visual_width,
)

ROOT = Path(__file__).resolve().parents[1]
CJK_FONT = Path.home() / ".cache" / "hyshell-fonts" / "NotoSansMonoCJKsc-Regular.otf"

# real SGR params observed from rich 15 static-render exports (prototype run)
RICH_SAMPLE = (
    "\x1b[31m╭─\x1b[0m 风险评估 \x1b[31m─╮\x1b[0m\n"
    "\x1b[1;31mDANGEROUS\x1b[0m rm -rf demo/*.log\n"
    "\x1b[3;33mитal风险\x1b[0m and \x1b[90mdim-ish\x1b[0m tail\n"
    "\x1b[38;5;196mX\x1b[0m \x1b[38;2;10;20;30mrgb\x1b[0m plain"
)


def test_sgr_parser_subset_handles_rich_output():
    lines = parse_ansi_lines(RICH_SAMPLE)
    assert len(lines) == 4
    # line 2: bold red run
    text2 = "".join(t for t, _ in lines[1])
    assert text2 == "DANGEROUS rm -rf demo/*.log"
    first_style = lines[1][0][1]
    assert first_style.bold and first_style.fg is not None
    # 256-color and truecolor runs parsed
    styles4 = {t: s for t, s in lines[3]}
    assert styles4["X"].fg == (255, 0, 0)
    assert styles4["rgb"].fg == (10, 20, 30)


def test_sgr_unknown_params_ignored():
    style = apply_sgr(Style(), [99, 999, 4])
    assert style == Style()  # nothing recognized, nothing broken
    reset = apply_sgr(apply_sgr(Style(), [1, 31]), [0])
    assert reset == Style()


def test_style_carries_across_lines():
    lines = parse_ansi_lines("\x1b[32mgreen\nstill-green\x1b[0m done")
    assert lines[1][0][1].fg is not None  # style persisted onto line 2


def test_wide_char_occupies_two_cells():
    assert visual_width("中") == 2
    assert visual_width("中a") == 3
    assert visual_width("──") == 2  # box drawing stays narrow (1 cell each)


def test_render_frame_ascii_geometry_and_ink(tmp_path):
    renderer = FrameRenderer(cols=40, rows=5, cjk_font_path=None)
    image = renderer.render("hello \x1b[31mworld\x1b[0m\nsecond line")
    assert image.size == renderer.size == (40 * 8 + 24, 5 * 18 + 24)
    colors = image.getcolors(maxcolors=100000)
    assert colors is not None and len(colors) > 1  # more than pure background
    assert any(color == BACKGROUND for _, color in colors)


def test_mini_gif_rendered(tmp_path):
    renderer = FrameRenderer(cols=40, rows=5, cjk_font_path=None)
    frames = [
        renderer.render("frame one\x1b[33m!\x1b[0m"),
        renderer.render("frame two\x1b[36m?\x1b[0m"),
    ]
    out = tmp_path / "mini.gif"
    assemble_gif(frames, [500, 500], out)
    with Image.open(out) as gif:
        assert gif.format == "GIF"
        assert gif.n_frames == 2
    assert out.stat().st_size < 200 * 1024


@pytest.mark.skipif(
    not CJK_FONT.exists(),
    reason="CJK font not cached (~/.cache/hyshell-fonts); only needed for GIF recording",
)
def test_cjk_render_no_crash_and_ink():
    renderer = FrameRenderer(cols=20, rows=2, cjk_font_path=CJK_FONT)
    image = renderer.render("\x1b[1m中文测试\x1b[0m ok")
    colors = image.getcolors(maxcolors=100000)
    assert colors is not None and len(colors) > 1


SHIPPED = [ROOT / "assets" / "demo-1-daily.gif", ROOT / "assets" / "demo-2-guard-fix.gif"]


@pytest.mark.parametrize("gif_path", SHIPPED, ids=[p.name for p in SHIPPED])
def test_shipped_gifs_valid(gif_path: Path):
    if not gif_path.exists():
        pytest.skip(f"{gif_path.name} 尚未录制(demo/record_gifs.py 生成后此测试生效)")
    assert gif_path.stat().st_size < 2 * 1024 * 1024, "issue requires < 2MB"
    with Image.open(gif_path) as gif:
        assert gif.format == "GIF"
        assert gif.n_frames > 1
        total_ms = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            total_ms += gif.info.get("duration", 0)
        assert total_ms <= 120_000, "issue requires <= 2 min playtime"
