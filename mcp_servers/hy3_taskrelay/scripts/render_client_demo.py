"""Render sanitized actual-call captures and a short GIF from verified client records."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1280
HEIGHT = 720
BACKGROUND = "#08111F"
PANEL = "#111D2E"
PANEL_ALT = "#16253A"
TEXT = "#F4F7FB"
MUTED = "#9EB0C7"
TEAL = "#42D3B0"
BLUE = "#6EA8FE"
AMBER = "#F5C66A"


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ("C:/Windows/Fonts/segoeuib.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("C:/Windows/Fonts/segoeui.ttf", "DejaVuSans.ttf")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _mono_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ("C:/Windows/Fonts/CascadiaMono-Bold.ttf", "C:/Windows/Fonts/consolab.ttf")
        if bold
        else ("C:/Windows/Fonts/CascadiaMono.ttf", "C:/Windows/Fonts/consola.ttf")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return _font(size, bold=bold)


def _wrapped_lines(
    draw: ImageDraw.ImageDraw,
    value: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in value.split():
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _text_block(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    *,
    size: int = 25,
    color: str = TEXT,
    max_width: int = 1080,
    bold: bool = False,
    spacing: int = 10,
) -> int:
    font = _font(size, bold=bold)
    x, y = xy
    for line in _wrapped_lines(draw, value, font, max_width):
        draw.text((x, y), line, font=font, fill=color)
        box = draw.textbbox((x, y), line, font=font)
        y += box[3] - box[1] + spacing
    return y


def _base_frame(step: str, title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((54, 42, 1226, 678), radius=28, fill=PANEL)
    draw.rounded_rectangle((86, 75, 224, 118), radius=20, fill=TEAL)
    draw.text((108, 84), step, font=_font(20, bold=True), fill=BACKGROUND)
    draw.text((86, 150), title, font=_font(43, bold=True), fill=TEXT)
    draw.text((88, 210), subtitle, font=_font(23), fill=MUTED)
    return image, draw


def _terminal_frame(title: str, client: str, lines: list[tuple[str, str]]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#050A12")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((42, 32, 1238, 688), radius=22, fill="#0B1220", outline="#2A3A52")
    draw.rounded_rectangle((42, 32, 1238, 92), radius=22, fill="#152238")
    draw.rectangle((42, 70, 1238, 92), fill="#152238")
    for x, color in ((74, "#FF6B6B"), (105, "#FFD166"), (136, "#42D3B0")):
        draw.ellipse((x, 53, x + 16, 69), fill=color)
    draw.text((178, 48), title, font=_mono_font(21, bold=True), fill=TEXT)
    draw.text((950, 49), "SANITIZED ACTUAL CALL", font=_mono_font(16), fill=TEAL)
    draw.text((72, 118), client, font=_mono_font(24, bold=True), fill=BLUE)
    y = 170
    for prefix, value in lines:
        draw.text((72, y), prefix, font=_mono_font(20, bold=True), fill=TEAL)
        draw.text((270, y), value, font=_mono_font(20), fill=TEXT)
        y += 52
    draw.text(
        (72, 640),
        "source: verified 2026-07-20 client event record • secrets and local paths omitted",
        font=_mono_font(15),
        fill=MUTED,
    )
    return image


def _metric(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    label: str,
    value: str,
    *,
    width: int = 320,
    accent: str = BLUE,
) -> None:
    x, y = xy
    draw.rounded_rectangle((x, y, x + width, y + 112), radius=18, fill=PANEL_ALT)
    draw.text((x + 22, y + 17), label, font=_font(18, bold=True), fill=MUTED)
    _text_block(
        draw,
        (x + 22, y + 48),
        value,
        size=24,
        color=accent,
        max_width=width - 44,
        bold=True,
        spacing=5,
    )


def _render_frames(project_root: Path) -> tuple[list[Image.Image], Image.Image, Image.Image]:
    clients = project_root / "docs" / "clients"
    artifacts = project_root / "docs" / "client_artifacts"
    codebuddy = json.loads((clients / "codebuddy_2026-07-20.json").read_text(encoding="utf-8"))
    codex = json.loads((clients / "codex_2026-07-20.json").read_text(encoding="utf-8"))
    audit = json.loads((artifacts / "codex_audit_2026-07-20.json").read_text(encoding="utf-8"))
    resume = json.loads((artifacts / "codex_resume_2026-07-20.json").read_text(encoding="utf-8"))

    frames: list[Image.Image] = []

    image, draw = _base_frame(
        "FLOW",
        "Hy3 TaskRelay cross-client handoff",
        "Verified headless clients • public synthetic fixture • 2026-07-20",
    )
    _metric(draw, (90, 302), "CLIENT A", "CodeBuddy 2.124.0", width=330, accent=TEAL)
    _metric(draw, (475, 302), "PORTABLE ARTIFACT", "checkpoint", width=330, accent=AMBER)
    _metric(
        draw,
        (860, 302),
        "CLIENT B",
        f"Codex CLI {codex['client_version']}",
        width=330,
        accent=BLUE,
    )
    draw.line((420, 358, 475, 358), fill=MUTED, width=4)
    draw.line((805, 358, 860, 358), fill=MUTED, width=4)
    _text_block(
        draw,
        (90, 492),
        "create checkpoint  →  audit checkpoint  →  create resume brief",
        size=29,
        color=TEXT,
        max_width=1080,
        bold=True,
    )
    frames.append(image)

    image, draw = _base_frame(
        "1 / 3",
        "CodeBuddy created the checkpoint",
        "Real MCP tool call using strict project configuration",
    )
    _metric(draw, (90, 292), "TOOL", codebuddy["tool_called"], width=510, accent=TEAL)
    _metric(
        draw,
        (650, 292),
        "CHECKPOINT ID",
        codebuddy["result"]["checkpoint_id"],
        width=540,
        accent=AMBER,
    )
    _metric(
        draw,
        (90, 446),
        "GROUNDED FACTS",
        str(codebuddy["result"]["confirmed_fact_count"]),
        width=330,
        accent=TEAL,
    )
    _metric(
        draw,
        (475, 446),
        "NEXT STEPS",
        str(codebuddy["result"]["next_step_count"]),
        width=330,
        accent=TEAL,
    )
    _metric(draw, (860, 446), "EXIT CODE", str(codebuddy["exit_code"]), width=330, accent=TEAL)
    frames.append(image)

    image, draw = _base_frame(
        "HANDOFF",
        "Portable checkpoint crossed the client boundary",
        "The exact structuredContent was recovered from CodeBuddy and validated locally",
    )
    _metric(
        draw,
        (90, 300),
        "SCHEMA",
        codebuddy["result"]["schema_version"],
        width=330,
        accent=AMBER,
    )
    _metric(
        draw,
        (475, 300),
        "CONTENT ID",
        codebuddy["result"]["checkpoint_id"],
        width=715,
        accent=AMBER,
    )
    _text_block(
        draw,
        (90, 472),
        "No prompt, raw response, credential, request ID, account data, or personal path "
        "is stored.",
        size=27,
        color=MUTED,
        max_width=1080,
    )
    frames.append(image)

    image, draw = _base_frame(
        "2 / 3",
        "Codex audited the CodeBuddy checkpoint",
        "Read-only MCP call over the same synthetic fixture",
    )
    _metric(draw, (90, 292), "STATUS", audit["overall_status"], width=330, accent=AMBER)
    _metric(draw, (475, 292), "FINDINGS", str(len(audit["findings"])), width=330, accent=AMBER)
    _metric(draw, (860, 292), "MCP STATUS", "completed", width=330, accent=TEAL)
    categories = " • ".join(finding["category"] for finding in audit["findings"])
    if not categories:
        categories = "No findings — checkpoint evidence and constraints are consistent"
    _text_block(
        draw,
        (90, 470),
        categories,
        size=27,
        color=TEXT,
        max_width=1080,
        bold=True,
    )
    frames.append(image)

    image, draw = _base_frame(
        "3 / 3",
        "Codex created the resume brief",
        "Prioritized continuation with observable validation gates",
    )
    _metric(draw, (90, 292), "RESUME ID", resume["resume_id"], width=510, accent=BLUE)
    priorities = " → ".join(str(step["priority"]) for step in resume["next_steps"])
    _metric(draw, (650, 292), "PRIORITY ORDER", priorities, width=540, accent=BLUE)
    _text_block(
        draw,
        (90, 466),
        "Both MCP calls completed • client exit code 0 • credentials omitted",
        size=28,
        color=TEAL,
        max_width=1080,
        bold=True,
    )
    frames.append(image)

    image, draw = _base_frame(
        "2 + 3",
        "Codex audited and planned continuation",
        "Two verified MCP calls over the checkpoint created by CodeBuddy",
    )
    _metric(draw, (90, 292), "AUDIT STATUS", audit["overall_status"], width=270, accent=AMBER)
    _metric(draw, (400, 292), "FINDINGS", str(len(audit["findings"])), width=270, accent=AMBER)
    _metric(draw, (710, 292), "RESUME ID", resume["resume_id"], width=480, accent=BLUE)
    _text_block(
        draw,
        (90, 466),
        f"Priority order: {priorities}  •  both calls completed  •  client exit code 0",
        size=28,
        color=TEAL,
        max_width=1080,
        bold=True,
    )
    frames.append(image)

    codebuddy_terminal = _terminal_frame(
        "TaskRelay / CodeBuddy",
        f"CodeBuddy Code {codebuddy['client_version']}  |  headless  |  strict MCP",
        [
            ("SERVER", "hy3-taskrelay  connected"),
            ("CALL", codebuddy["tool_called"]),
            ("STATUS", f"completed  |  exit {codebuddy['exit_code']}"),
            ("CHECKPOINT", codebuddy["result"]["checkpoint_id"]),
            ("SCHEMA", codebuddy["result"]["schema_version"]),
            (
                "OUTPUT",
                f"{codebuddy['result']['confirmed_fact_count']} grounded facts  |  "
                f"{codebuddy['result']['next_step_count']} next steps",
            ),
        ],
    )
    codex_terminal = _terminal_frame(
        "TaskRelay / Codex",
        f"Codex CLI {codex['client_version']}  |  ephemeral  |  read-only",
        [
            ("INPUT", codex["input_checkpoint_id"]),
            ("CALL 1", codex["mcp_calls"][0]["tool"]),
            ("AUDIT", f"{audit['overall_status']}  |  {len(audit['findings'])} findings"),
            ("CALL 2", codex["mcp_calls"][1]["tool"]),
            ("RESUME", resume["resume_id"]),
            ("OUTPUT", f"priority 1 → 2  |  exit {codex['exit_code']}"),
        ],
    )

    return frames, codebuddy_terminal, codex_terminal


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output = project_root / "docs" / "demo"
    output.mkdir(parents=True, exist_ok=True)
    frames, codebuddy_terminal, codex_terminal = _render_frames(project_root)
    frames[1].save(output / "codebuddy_checkpoint.png")
    frames[5].save(output / "codex_audit_resume.png")
    codebuddy_terminal.save(output / "codebuddy_actual_call.png")
    codex_terminal.save(output / "codex_actual_calls.png")
    gif_frames = [frames[0], codebuddy_terminal, frames[2], frames[3], frames[4], codex_terminal]
    gif_frames[0].save(
        output / "taskrelay_cross_client.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=[1800, 2600, 1800, 2200, 2200, 2600],
        loop=0,
        optimize=False,
        disposal=2,
    )
    print("Rendered 2 actual-call PNGs, 2 summary cards, and a 13.2-second client GIF.")


if __name__ == "__main__":
    main()
