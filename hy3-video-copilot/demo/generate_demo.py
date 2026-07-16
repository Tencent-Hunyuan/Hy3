"""
Demo script for Hy3 Video Copilot.
Generates a sample video and runs both end-to-end flows.
"""
import subprocess
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from video_processor import VideoProcessor

DEMO_DIR = Path(__file__).parent
ASSETS_DIR = DEMO_DIR / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

SAMPLE_VIDEO = ASSETS_DIR / "sample_video.mp4"
EDITED_VIDEO = ASSETS_DIR / "edited_video.mp4"
FRAME_OUTPUT = ASSETS_DIR / "keyframe.jpg"
AUDIO_OUTPUT = ASSETS_DIR / "audio.mp3"

vp = VideoProcessor()


def create_sample_video():
    print("[1/4] Creating sample video...")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=15:size=640x360:rate=30",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-shortest",
        str(SAMPLE_VIDEO),
    ], check=True, capture_output=True)
    duration = vp.get_duration(str(SAMPLE_VIDEO))
    print(f"    Created: {SAMPLE_VIDEO.name} ({duration:.1f}s)")


def demo_smart_edit():
    print("\n[2/4] Demo: Smart Edit (NL → Editing Commands)")
    print("    Instruction: 'Trim first 3 seconds, speed up remaining to 2x, add fade-out'")

    commands = [
        ("trim starting at 3s", lambda: vp.trim(str(SAMPLE_VIDEO), 3, 12, str(ASSETS_DIR / "step1_trimmed.mp4"))),
        ("speed up 2x", lambda: vp.speed(str(ASSETS_DIR / "step1_trimmed.mp4"), 2.0, str(ASSETS_DIR / "step2_speed.mp4"))),
        ("fade out 1s", lambda: vp.fade_out(str(ASSETS_DIR / "step2_speed.mp4"), 1.0, str(EDITED_VIDEO))),
    ]

    current = str(SAMPLE_VIDEO)
    for desc, fn in commands:
        current = fn()
        dur = vp.get_duration(current)
        print(f"    ✓ {desc} → {Path(current).name} ({dur:.1f}s)")

    print(f"    ✓ Final output: {EDITED_VIDEO.name}")


def demo_video_analysis():
    print("\n[3/4] Demo: Video Analysis")
    meta = vp.get_metadata(str(SAMPLE_VIDEO))

    print(f"    Format: {meta['format']['format_name']}")
    print(f"    Duration: {float(meta['format']['duration']):.1f}s")
    print(f"    Size: {int(int(meta['format']['size']) / 1024)}KB")

    for s in meta["streams"]:
        kind = s["codec_type"]
        if kind == "video":
            print(f"    Video: {s['codec_name']} {s['width']}x{s['height']} @ {s.get('r_frame_rate', 'N/A')} fps")
        elif kind == "audio":
            print(f"    Audio: {s['codec_name']} {s.get('sample_rate', 'N/A')}Hz")

    # Extract a keyframe and audio for analysis demo
    vp.extract_frame(str(SAMPLE_VIDEO), 7.5, str(FRAME_OUTPUT))
    vp.extract_audio(str(SAMPLE_VIDEO), str(AUDIO_OUTPUT))
    print(f"    ✓ Keyframe: {FRAME_OUTPUT.name}")
    print(f"    ✓ Audio: {AUDIO_OUTPUT.name}")


def generate_demo_gif():
    print("\n[4/4] Generating demo GIF from frontend...")
    gif_path = DEMO_DIR / "hy3-video-copilot-demo.gif"

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "x11grab",
        "-framerate", "10",
        "-video_size", "1280x720",
        "-i", ":0.0",
        "-t", "60",
        "-vf", "fps=10,scale=800:-1:flags=lanczos",
        str(gif_path),
    ], check=True)
    print(f"    GIF saved: {gif_path}")


if __name__ == "__main__":
    create_sample_video()
    demo_smart_edit()
    demo_video_analysis()

    if "--record-gif" in sys.argv:
        print("\n⚠️  Recording desktop in 5 seconds. Switch to browser window!")
        time.sleep(5)
        generate_demo_gif()

    print("\n✅ Demo complete!")
    print(f"\nAssets: {ASSETS_DIR}")
