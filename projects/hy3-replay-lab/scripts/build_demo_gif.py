from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

FRAME_NAMES = (
    "01-case-picker.png",
    "02-coding-divergence.png",
    "03-coding-evidence.png",
    "04-research-divergence.png",
    "05-research-evidence.png",
)
FRAME_DURATIONS_MS = (1_600, 2_600, 2_600, 2_600, 2_600)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ReplayLab actual-UI demo GIF.")
    parser.add_argument(
        "--demo-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "demo",
    )
    arguments = parser.parse_args()
    frames_dir = arguments.demo_dir / "frames"
    source_paths = [frames_dir / name for name in FRAME_NAMES]
    missing = [path.name for path in source_paths if not path.is_file()]
    if missing:
        raise SystemExit(f"missing demo frames: {', '.join(missing)}")

    frames: list[Image.Image] = []
    for source in source_paths:
        with Image.open(source) as image:
            width = 960
            height = round(image.height * width / image.width)
            resized = image.convert("RGB").resize(
                (width, height), Image.Resampling.LANCZOS
            )
            frames.append(
                resized.quantize(colors=192, method=Image.Quantize.MEDIANCUT)
            )

    output = arguments.demo_dir / "replaylab-offline-demo.gif"
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATIONS_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"demo GIF: {output}")
    print(f"duration: {sum(FRAME_DURATIONS_MS) / 1_000:.1f}s")


if __name__ == "__main__":
    main()
