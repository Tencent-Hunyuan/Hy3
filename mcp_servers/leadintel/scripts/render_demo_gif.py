from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    frames = []
    font = ImageFont.load_default()
    slides = [
        ("Hy3 LeadIntel MCP", "stdio server starts in offline demo mode"),
        ("initialize", "MCP ClientSession connects successfully"),
        ("tools/list", "5 tools: analyze, query, outreach, batch, status"),
        ("hy3_leadintel_status", "mode=offline, model=hy3, key is not exposed"),
        ("analyze_lead", "Aurora Motion GmbH -> P0, score=100"),
        ("ready for real Hy3", "set HY3_API_KEY and HY3_API_BASE"),
    ]
    for title, body in slides:
        image = Image.new("RGB", (860, 420), "#f7f7f2")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 860, 72), fill="#1f3a5f")
        draw.text((28, 25), "[OFFLINE DEMO MODE]", fill="#ffffff", font=font)
        draw.text((52, 130), title, fill="#17202a", font=font)
        draw.text((52, 190), body, fill="#334155", font=font)
        draw.rounded_rectangle((52, 270, 808, 340), radius=8, outline="#2f855a", width=3)
        draw.text((78, 296), "MCP stdio flow verified by scripts/sdk_stdio_client.py", fill="#2f855a", font=font)
        frames.append(image)

    out = ROOT / "assets" / "demo.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=1100, loop=0)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
