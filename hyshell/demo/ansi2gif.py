# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Render ANSI (SGR subset) terminal frames into an animated GIF with Pillow.

Design notes:

* rich's static renderables export a **pure SGR** stream (verified on rich 15
  — no cursor-movement escapes), so a small SGR-only parser is sufficient;
  unknown SGR parameters are ignored, never fatal.
* Cell layout mirrors rich exactly: character cell width comes from
  ``rich.cells.get_character_cell_size`` (wide CJK = 2 cells), so box-drawing
  panels stay aligned pixel-perfectly.
* Narrow glyphs use the first monospace TTF found among common system paths
  (DejaVu on Debian/Fedora/Arch, Menlo on macOS); if none exists, PIL's
  built-in bitmap font is used with a warning (degraded rendering, no crash).
  Wide glyphs use Noto Sans Mono CJK SC (downloaded once by ``fetch_font.py``
  into ``~/.cache/hyshell-fonts/`` — never committed to the repo).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from rich.cells import get_character_cell_size

# (regular, bold) monospace font path pairs — most common locations first.
_MONO_FONT_CANDIDATES: tuple[tuple[str, str], ...] = (
    (  # Debian / Ubuntu
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ),
    (  # Fedora
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Bold.ttf",
    ),
    (  # Arch (ttf-dejavu)
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
    ),
    (  # macOS
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Menlo.ttc",
    ),
)


def _load_mono_fonts(font_size: int) -> tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
    """Load a (regular, bold) monospace pair from common system paths.

    Falls back to PIL's built-in bitmap font — with a printed warning and
    visibly degraded rendering — so re-recording never crashes on systems
    without a known monospace TTF."""
    for regular, bold in _MONO_FONT_CANDIDATES:
        if Path(regular).exists():
            bold_path = bold if Path(bold).exists() else regular
            return (
                ImageFont.truetype(regular, font_size),
                ImageFont.truetype(bold_path, font_size),
            )
    print(
        "警告:未找到系统等宽 TTF 字体(DejaVu/Menlo 等),退回 Pillow 内置点阵字体——"
        "GIF 仍可生成但渲染效果明显变差;建议安装 DejaVu Sans Mono 后重录。",
        file=sys.stderr,
    )
    fallback = ImageFont.load_default()
    return fallback, fallback

BACKGROUND = (18, 18, 26)
FOREGROUND = (230, 230, 230)

# Dark-theme 16-color palette (indices 30-37 normal, 90-97 bright).
_ANSI16: dict[int, tuple[int, int, int]] = {
    30: (58, 58, 70),
    31: (232, 80, 80),
    32: (92, 200, 120),
    33: (240, 200, 90),
    34: (100, 140, 240),
    35: (200, 120, 220),
    36: (95, 200, 210),
    37: (220, 220, 225),
    90: (110, 110, 125),
    91: (255, 120, 120),
    92: (130, 235, 160),
    93: (255, 225, 130),
    94: (140, 175, 255),
    95: (230, 150, 245),
    96: (135, 230, 240),
    97: (245, 245, 250),
}


def _xterm256(n: int) -> tuple[int, int, int]:
    """Standard xterm 256-color palette."""
    if n < 16:
        base = _ANSI16[(30 + n) if n < 8 else (90 + n - 8)]
        return base
    if n < 232:
        n -= 16
        r, g, b = n // 36, (n // 6) % 6, n % 6
        scale = [0, 95, 135, 175, 215, 255]
        return (scale[r], scale[g], scale[b])
    gray = 8 + (n - 232) * 10
    return (gray, gray, gray)


@dataclass(frozen=True)
class Style:
    """Current SGR state."""

    fg: tuple[int, int, int] | None = None
    bg: tuple[int, int, int] | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False


def apply_sgr(style: Style, params: list[int]) -> Style:
    """Apply one SGR escape's parameters; unknown codes are ignored."""
    index = 0
    while index < len(params):
        code = params[index]
        if code == 0:
            style = Style()
        elif code == 1:
            style = replace(style, bold=True)
        elif code == 2:
            style = replace(style, dim=True)
        elif code == 3:
            style = replace(style, italic=True)
        elif code == 22:
            style = replace(style, bold=False, dim=False)
        elif code == 23:
            style = replace(style, italic=False)
        elif code == 39:
            style = replace(style, fg=None)
        elif code == 49:
            style = replace(style, bg=None)
        elif 30 <= code <= 37 or 90 <= code <= 97:
            style = replace(style, fg=_ANSI16[code])
        elif 40 <= code <= 47:
            style = replace(style, bg=_ANSI16[code - 10])
        elif 100 <= code <= 107:
            style = replace(style, bg=_ANSI16[code - 10])
        elif code in (38, 48):
            target = "fg" if code == 38 else "bg"
            if index + 1 < len(params) and params[index + 1] == 5 and index + 2 < len(params):
                color = _xterm256(params[index + 2])
                style = replace(style, **{target: color})
                index += 2
            elif index + 1 < len(params) and params[index + 1] == 2 and index + 4 < len(params):
                color = (params[index + 2], params[index + 3], params[index + 4])
                style = replace(style, **{target: color})
                index += 4
            else:  # malformed extended color — ignore the rest
                break
        # anything else: ignore silently
        index += 1
    return style


_SGR_RE = re.compile(r"(\x1b\[[0-9;]*m)")


def parse_ansi_lines(text: str) -> list[list[tuple[str, Style]]]:
    """Parse ANSI text into per-line lists of (text, style) runs.

    Style state carries across lines, matching terminal behaviour.
    """
    lines: list[list[tuple[str, Style]]] = []
    style = Style()
    for raw_line in text.split("\n"):
        runs: list[tuple[str, Style]] = []
        for token in _SGR_RE.split(raw_line):
            if not token:
                continue
            if token.startswith("\x1b["):
                params = [int(p) if p else 0 for p in token[2:-1].split(";")]
                style = apply_sgr(style, params)
            else:
                runs.append((token, style))
        lines.append(runs)
    return lines


def visual_width(text: str) -> int:
    """Cell width of ``text`` using rich's own cell-size rules."""
    return sum(get_character_cell_size(char) for char in text)


class FrameRenderer:
    """Draws one ANSI text block into a fixed-size terminal image."""

    def __init__(
        self,
        cols: int = 80,
        rows: int = 34,
        cell_w: int = 8,
        cell_h: int = 18,
        font_size: int = 16,
        cjk_font_path: Path | None = None,
        padding: int = 12,
    ) -> None:
        self.cols = cols
        self.rows = rows
        self.cell_w = cell_w
        self.cell_h = cell_h
        self.padding = padding
        self.font, self.font_bold = _load_mono_fonts(font_size)
        self.font_cjk = (
            ImageFont.truetype(str(cjk_font_path), font_size) if cjk_font_path else None
        )

    @property
    def size(self) -> tuple[int, int]:
        return (
            self.cols * self.cell_w + 2 * self.padding,
            self.rows * self.cell_h + 2 * self.padding,
        )

    def render(self, ansi_text: str) -> Image.Image:
        image = Image.new("RGB", self.size, BACKGROUND)
        draw = ImageDraw.Draw(image)
        lines = parse_ansi_lines(ansi_text)[-self.rows :]
        for row, runs in enumerate(lines):
            x_cells = 0
            y = self.padding + row * self.cell_h
            for text, style in runs:
                for char in text:
                    width = get_character_cell_size(char)
                    if width <= 0:
                        continue  # combining/control chars: skip
                    if x_cells + width > self.cols:
                        break
                    x = self.padding + x_cells * self.cell_w
                    if style.bg is not None:
                        draw.rectangle(
                            (x, y, x + width * self.cell_w - 1, y + self.cell_h - 1),
                            fill=style.bg,
                        )
                    if char != " ":
                        color = style.fg or FOREGROUND
                        if style.dim:
                            color = tuple(int(c * 0.6) for c in color)
                        if width == 2 and self.font_cjk is not None:
                            font = self.font_cjk
                        elif width == 2:
                            font = self.font  # tofu fallback; recorder ensures CJK font
                        else:
                            font = self.font_bold if style.bold else self.font
                        draw.text((x, y + 1), char, font=font, fill=color)
                    x_cells += width
                else:
                    continue
                break  # inner loop hit right edge
        return image


def assemble_gif(
    frames: list[Image.Image],
    durations_ms: list[int],
    out_path: Path,
    colors: int = 64,
) -> None:
    """Quantize frames and write a looping GIF."""
    if not frames:
        raise ValueError("no frames to assemble")
    if len(frames) != len(durations_ms):
        raise ValueError("frames and durations length mismatch")
    quantized = [f.convert("P", palette=Image.ADAPTIVE, colors=colors) for f in frames]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        out_path,
        save_all=True,
        append_images=quantized[1:],
        duration=durations_ms,
        loop=0,
        optimize=True,
    )
