from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    frames = []
    font = ImageFont.load_default()
    slides = [
        ("Hy3 LeadIntel MCP", "Two real MCP clients verified the stdio server."),
        ("Claude Code CLI 2.1.146", "claude mcp list -> hy3-leadintel-verify: ✓ Connected"),
        ("Claude tool call", "claude -p called hy3_leadintel_status and returned JSON."),
        ("MCP Inspector CLI 1.0.0", "tools/list returned 5 tools from the server."),
        ("Inspector tool call", "tools/call hy3_leadintel_status -> isError: false"),
        ("Ready for real Hy3", "Set HY3_API_KEY and HY3_API_BASE to leave offline mode."),
    ]
    for title, body in slides:
        image = Image.new("RGB", (860, 420), "#f7f7f2")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 860, 72), fill="#1f3a5f")
        draw.text((28, 25), "[OFFLINE DEMO MODE]", fill="#ffffff", font=font)
        draw.text((52, 130), title, fill="#17202a", font=font)
        draw.text((52, 190), body, fill="#334155", font=font)
        draw.rounded_rectangle((52, 270, 808, 340), radius=8, outline="#2f855a", width=3)
        draw.text((78, 296), "Evidence: assets/client_verification.md + demo_transcript.json", fill="#2f855a", font=font)
        frames.append(image)

    out = ROOT / "assets" / "demo.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=1100, loop=0)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
