import pytest
import subprocess
from pathlib import Path
from video_processor import VideoProcessor

vp = VideoProcessor()
FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_VIDEO = FIXTURE_DIR / "test_input.mp4"


@pytest.fixture(scope="session")
def sample_video():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    if not FIXTURE_VIDEO.exists():
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "testsrc=duration=10:size=640x360:rate=30",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-shortest",
            str(FIXTURE_VIDEO),
        ], check=True, capture_output=True)
    return str(FIXTURE_VIDEO)


def test_get_metadata(sample_video):
    meta = vp.get_metadata(sample_video)
    assert "format" in meta
    assert "streams" in meta


def test_get_duration(sample_video):
    duration = vp.get_duration(sample_video)
    assert duration == pytest.approx(10.0, rel=0.1)


def test_trim(sample_video, tmp_path):
    output = str(tmp_path / "trimmed.mp4")
    result = vp.trim(sample_video, 0, 5, output)
    assert Path(result).exists()
    assert vp.get_duration(result) == pytest.approx(5.0, rel=0.1)


def test_fade_in(sample_video, tmp_path):
    output = str(tmp_path / "fade_in.mp4")
    result = vp.fade_in(sample_video, 1.0, output)
    assert Path(result).exists()


def test_fade_out(sample_video, tmp_path):
    output = str(tmp_path / "fade_out.mp4")
    result = vp.fade_out(sample_video, 1.0, output)
    assert Path(result).exists()


def test_speed(sample_video, tmp_path):
    output = str(tmp_path / "speed.mp4")
    result = vp.speed(sample_video, 2.0, output)
    assert Path(result).exists()
    assert vp.get_duration(result) == pytest.approx(5.0, rel=0.3)


def test_extract_frame(sample_video, tmp_path):
    output = str(tmp_path / "frame.jpg")
    result = vp.extract_frame(sample_video, 5.0, output)
    assert Path(result).exists()
    assert result.endswith(".jpg")


def test_extract_audio(sample_video, tmp_path):
    output = str(tmp_path / "audio.mp3")
    result = vp.extract_audio(sample_video, output)
    assert Path(result).exists()
    assert result.endswith(".mp3")
