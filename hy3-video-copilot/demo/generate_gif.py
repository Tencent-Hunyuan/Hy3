"""
Generate demo GIF showing before/after video editing.
"""
import subprocess
from pathlib import Path

DEMO_DIR = Path(__file__).parent
ASSETS_DIR = DEMO_DIR / "assets"
OUTPUT_GIF = DEMO_DIR / "hy3-video-copilot-demo.gif"
COMPARISON_VIDEO = ASSETS_DIR / "comparison.mp4"


def create_comparison_video():
    print("Creating side-by-side comparison video...")

    sample = str(ASSETS_DIR / "sample_video.mp4")
    edited = str(ASSETS_DIR / "edited_video.mp4")

    if not Path(sample).exists() or not Path(edited).exists():
        print("Run generate_demo.py first!")
        return False

    subprocess.run([
        "ffmpeg", "-y",
        "-i", sample,
        "-i", edited,
        "-filter_complex",
        "[0:v]scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,setpts=PTS,setsar=1[orig];"
        "[1:v]scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,setpts=PTS,setsar=1[edit];"
        "[orig][edit]hstack=inputs=2,drawtext=text='Before':x=80:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.5,"
        "drawtext=text='After':x=400:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.5[out]",
        "-map", "[out]",
        "-t", "6",
        str(COMPARISON_VIDEO),
    ], check=True, capture_output=True)
    print(f"  Created: {COMPARISON_VIDEO.name}")
    return True


def generate_gif():
    print("Converting to GIF...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(COMPARISON_VIDEO),
        "-vf", "fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=64[p];[s1][p]paletteuse=dither=bayer",
        "-loop", "0",
        str(OUTPUT_GIF),
    ], check=True, capture_output=True)
    print(f"  GIF saved: {OUTPUT_GIF.name} ({OUTPUT_GIF.stat().st_size / 1024:.0f}KB)")


if __name__ == "__main__":
    if create_comparison_video():
        generate_gif()
        print("\n✅ Demo GIF ready!")
