"""Execute the Inspector demo and render its real terminal output as an animated GIF."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = SCRIPT_DIR.parent / "docs" / "demo.gif"


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        os.getenv("MCP_DEMO_FONT", ""),
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def render(lines: list[str], *, width: int = 1280, height: int = 720) -> Image.Image:
    image = Image.new("RGB", (width, height), "#0d1117")
    draw = ImageDraw.Draw(image)
    body_font = font(21)
    title_font = font(17)
    draw.rounded_rectangle((18, 18, width - 18, height - 18), radius=12, fill="#161b22")
    draw.ellipse((38, 36, 52, 50), fill="#ff5f56")
    draw.ellipse((62, 36, 76, 50), fill="#ffbd2e")
    draw.ellipse((86, 36, 100, 50), fill="#27c93f")
    draw.text((118, 33), "MCP Inspector CLI", font=title_font, fill="#8b949e")
    visible = lines[-26:]
    y = 72
    for line in visible:
        color = "#58a6ff" if line.startswith("$") else "#c9d1d9"
        if line.startswith(("PASS", "Call succeeded")):
            color = "#3fb950"
        draw.text((42, y), line, font=body_font, fill=color)
        y += 24
    draw.rectangle(
        (42, min(y + 2, height - 42), 54, min(y + 22, height - 22)), fill="#c9d1d9"
    )
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    command = [sys.executable, str(SCRIPT_DIR / "run_inspector_demo.py")]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    terminal_lines: list[str] = []
    frames: list[Image.Image] = [
        render(["Starting reproducible MCP integration test..."])
    ]
    durations: list[int] = [900]
    last_frame_time = time.monotonic()

    for raw_line in process.stdout:
        clean = ANSI_ESCAPE.sub("", raw_line.rstrip())
        wrapped = textwrap.wrap(clean, width=94, replace_whitespace=False) or [""]
        terminal_lines.extend(wrapped)
        now = time.monotonic()
        delay = max(260, min(1800, int((now - last_frame_time) * 1000)))
        frames.append(render(terminal_lines))
        durations.append(delay)
        last_frame_time = now
        print(clean, flush=True)

    return_code = process.wait()
    if return_code:
        print(f"Demo command failed with exit code {return_code}", file=sys.stderr)
        return return_code

    frames.extend([render(terminal_lines), render(terminal_lines)])
    durations.extend([1200, 2200])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"GIF written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
