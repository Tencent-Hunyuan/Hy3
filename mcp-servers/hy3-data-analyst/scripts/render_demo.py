"""Render the verified stdio smoke-test transcript as an animated GIF."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PACKAGE_ROOT / "docs" / "demo.gif"
FONT_PATH = Path("/System/Library/Fonts/Menlo.ttc")

STAGES = [
    ["$ uv run --no-sync python scripts/check_mcp.py"],
    [
        "$ uv run --no-sync python scripts/check_mcp.py",
        "MCP initialize: OK (3 tools)",
    ],
    [
        "$ uv run --no-sync python scripts/check_mcp.py",
        "MCP initialize: OK (3 tools)",
        "Tools: analyze_dataset, generate_data_report,",
        "       profile_dataset",
    ],
    [
        "$ uv run --no-sync python scripts/check_mcp.py",
        "MCP initialize: OK (3 tools)",
        "Tools: analyze_dataset, generate_data_report,",
        "       profile_dataset",
        "profile_dataset: OK (6 rows, sample_rows=2)",
    ],
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if FONT_PATH.exists():
        return ImageFont.truetype(str(FONT_PATH), size=size)
    return ImageFont.load_default()


def render_stage(lines: list[str], stage: int) -> Image.Image:
    image = Image.new("RGB", (960, 540), "#0b1020")
    draw = ImageDraw.Draw(image)
    title_font = load_font(22)
    body_font = load_font(20)
    label_font = load_font(14)

    draw.text((48, 38), "Hy3 Data Analyst MCP", font=title_font, fill="#f3f4f6")
    draw.text((48, 74), "verified stdio client round trip", font=label_font, fill="#93c5fd")

    terminal = (48, 116, 912, 474)
    draw.rounded_rectangle(terminal, radius=14, fill="#111827", outline="#334155", width=2)
    for x, color in ((72, "#fb7185"), (96, "#fbbf24"), (120, "#34d399")):
        draw.ellipse((x - 7, 137, x + 7, 151), fill=color)
    draw.text((734, 132), "MCP / stdio", font=label_font, fill="#64748b")

    y = 188
    for index, line in enumerate(lines):
        color = "#86efac" if index == 0 else "#e5e7eb"
        draw.text((76, y), line, font=body_font, fill=color)
        y += 46
    if stage < len(STAGES) - 1:
        draw.rectangle((76, y + 2, 87, y + 25), fill="#86efac")

    draw.text((48, 504), f"step {stage + 1}/{len(STAGES)}", font=label_font, fill="#64748b")
    return image


def main() -> None:
    frames = [render_stage(lines, index) for index, lines in enumerate(STAGES)]
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=[1600, 1800, 2400, 3600],
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
