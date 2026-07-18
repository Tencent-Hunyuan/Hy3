# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Render assets/demo_transcript.json into assets/demo.gif with Pillow.

Terminal-style frames: dark background, monospace font, simple syntax
colors.  Keeps the GIF well under 2MB via adaptive palette quantization.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # Pillow is the optional [demo] extra, not a core dependency
    sys.exit(
        "render_gif.py needs Pillow — install the demo extra first: "
        "pip install '.[demo]' (run from mcp-server/)"
    )

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SIZE = 15
LINE_H = 20
COLS = 78
ROWS = 27  # body rows per frame
PAD = 14

BG = (13, 17, 23)
FG = (201, 209, 217)
TITLE = (88, 166, 255)
CMD = (126, 231, 135)
BANNER = (240, 198, 116)
DIM = (139, 148, 158)
RULE = (48, 54, 61)

#: per-frame display time (ms); first and last frames linger longer
DUR_FIRST, DUR_MID, DUR_LAST = 3800, 3200, 4500


def _color(line: str) -> tuple[int, int, int]:
    if "OFFLINE DEMO MODE" in line or line.startswith("***"):
        return BANNER
    if line.startswith("$"):
        return CMD
    if line.startswith(("->", "#")):
        return DIM
    if line.startswith(">"):
        return BANNER
    return FG


def render(transcript_path: Path, gif_path: Path) -> None:
    frames_spec = json.loads(transcript_path.read_text(encoding="utf-8"))
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    char_w = font.getlength("M")
    width = int(PAD * 2 + COLS * char_w)
    height = PAD * 2 + LINE_H * (ROWS + 2)

    images: list[Image.Image] = []
    for spec in frames_spec:
        img = Image.new("RGB", (width, height), BG)
        draw = ImageDraw.Draw(img)
        y = PAD
        draw.text((PAD, y), spec["title"][:COLS], font=font, fill=TITLE)
        y += LINE_H
        draw.line((PAD, y + 4, width - PAD, y + 4), fill=RULE, width=1)
        y += LINE_H // 2
        for line in spec["lines"][:ROWS]:
            ascii_line = line.encode("ascii", "replace").decode()[:COLS]
            draw.text((PAD, y), ascii_line, font=font, fill=_color(line))
            y += LINE_H
        images.append(img.convert("P", palette=Image.Palette.ADAPTIVE, colors=48))

    durations = (
        [DUR_FIRST] + [DUR_MID] * max(0, len(images) - 2) + [DUR_LAST]
        if len(images) > 1
        else [DUR_FIRST]
    )
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    size = gif_path.stat().st_size
    print(f"[render_gif] {gif_path} : {len(images)} frames, {size / 1024:.0f} KiB")
    if size >= 2_000_000:
        print("[render_gif] WARNING: GIF is >= 2MB", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    render(
        MCP_SERVER_DIR / "assets" / "demo_transcript.json",
        MCP_SERVER_DIR / "assets" / "demo.gif",
    )
