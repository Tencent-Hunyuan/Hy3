import subprocess
import json
import tempfile
import os
from pathlib import Path
from typing import Optional


class VideoProcessor:
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path

    def get_metadata(self, video_path: str) -> dict:
        cmd = [
            self.ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)

    def trim(self, video_path: str, start: float, duration: float, output_path: str) -> str:
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-ss", str(start),
            "-t", str(duration),
            "-c", "copy",
            output_path,
            "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def fade_in(self, video_path: str, fade_duration: float, output_path: str) -> str:
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-vf", f"fade=t=in:st=0:d={fade_duration}",
            "-c:a", "copy",
            output_path,
            "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def fade_out(self, video_path: str, fade_duration: float, output_path: str) -> str:
        duration = self.get_duration(video_path)
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-vf", f"fade=t=out:st={duration - fade_duration}:d={fade_duration}",
            "-c:a", "copy",
            output_path,
            "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def get_duration(self, video_path: str) -> float:
        cmd = [
            self.ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())

    def extract_audio(self, video_path: str, output_path: str) -> str:
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-vn", "-acodec", "mp3",
            output_path, "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def extract_frame(self, video_path: str, time: float, output_path: str) -> str:
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-ss", str(time),
            "-vframes", "1",
            output_path, "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def concat(self, video_paths: list[str], output_path: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for p in video_paths:
                f.write(f"file '{Path(p).absolute()}'\n")
            list_path = f.name

        cmd = [
            self.ffmpeg, "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            output_path, "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        os.unlink(list_path)
        return output_path

    def speed(self, video_path: str, factor: float, output_path: str) -> str:
        cmd = [
            self.ffmpeg, "-i", video_path,
            "-filter:v", f"setpts={1/factor}*PTS",
            "-filter:a", f"atempo={factor}",
            output_path, "-y",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
