"""Render a terminal-style GIF from the verified, non-sensitive EvalForge artifacts."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - handled only in minimal user environments
    raise SystemExit("render_demo.py requires Pillow; install with: pip install .[dev]") from exc

WIDTH, HEIGHT = 1280, 720
FONT_PATH = Path(r"C:\Windows\Fonts\consola.ttf")


def _frame(lines: list[tuple[str, str]]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#0c111b")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 52), fill="#1f2937")
    title_font = ImageFont.truetype(str(FONT_PATH), 24)
    body_font = ImageFont.truetype(str(FONT_PATH), 25)
    draw.text((26, 13), "Windows PowerShell — Hy3 EvalForge live validation", font=title_font)
    y = 90
    for color, line in lines:
        draw.text((42, y), line, fill=color, font=body_font)
        y += 48
    return image


def main() -> None:
    root = Path(__file__).parents[1]
    comparison_path = (
        root
        / "examples"
        / "support_agent_regression"
        / "runs"
        / "baseline_vs_candidate.comparison.json"
    )
    calibration_path = root / "evals" / "calibration_results.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    if comparison["status"] != "BLOCKED" or calibration["case_count"] != 30:
        raise SystemExit("Expected live-validation artifacts are unavailable or inconsistent.")
    accuracy = f"{calibration['pairwise_accuracy']:.1%}"
    prompt = r"PS D:\hy3_evalforge> "
    scenes = [
        [("#e5e7eb", prompt + "python scripts\\live_eval.py")],
        [
            ("#e5e7eb", prompt + "python scripts\\live_eval.py"),
            ("#86efac", "Real Hy3 comparison complete: BLOCKED;"),
            ("#86efac", "runs\\baseline_vs_candidate.report.md"),
        ],
        [("#e5e7eb", prompt + '$env:EVALFORGE_ALLOW_EXPENSIVE="1"')],
        [
            ("#e5e7eb", prompt + '$env:EVALFORGE_ALLOW_EXPENSIVE="1"'),
            ("#e5e7eb", prompt + "python scripts\\calibrate_pairwise.py"),
        ],
        [
            ("#e5e7eb", prompt + "python scripts\\calibrate_pairwise.py"),
            ("#86efac", f"Calibration complete: {accuracy}; evals\\calibration_results.json"),
        ],
        [
            ("#fbbf24", "Verified Hy3 EvalForge result"),
            ("#86efac", "Regression status: BLOCKED"),
            ("#86efac", f"Pairwise calibration: {accuracy} (27 / 30)"),
            ("#cbd5e1", "No API key or environment-variable value is displayed."),
        ],
    ]
    output_dir = root / "demo"
    output_dir.mkdir(exist_ok=True)
    frames = [_frame(scene) for scene in scenes]
    frames[0].save(
        output_dir / "hy3_evalforge_terminal_demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[1000, 2200, 1000, 1500, 2200, 2600],
        loop=0,
        optimize=True,
    )
    print("Wrote demo/hy3_evalforge_terminal_demo.gif")


if __name__ == "__main__":
    main()
