"""Helpers for downloading and processing videos."""
from pathlib import Path
import subprocess
from typing import List, Optional



def _run(command: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def download_youtube(url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    template = output_dir / "source.%(ext)s"
    command = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio/best", "-o", str(template), url]
    _run(command)

    matches = list(output_dir.glob("source.*"))
    if not matches:
        raise FileNotFoundError("yt-dlp did not produce a video file")
    return matches[0]


def get_video_duration(video_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = _run(command)
    return float(result.stdout.strip() or 0)


def extract_audio(video_path: Path, audio_path: Path) -> None:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    _run(command)


def sample_frames(video_path: Path, frames_dir: Path, max_frames: int = 10) -> List[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    duration = get_video_duration(video_path)
    if duration <= 0:
        raise ValueError("Unable to determine video duration for frame sampling")
    interval = max(duration / max_frames, 1)
    fps_value = 1 / interval
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps_value}",
        "-frames:v",
        str(max_frames),
        str(frames_dir / "frame_%03d.jpg"),
    ]
    _run(command)
    return sorted(frames_dir.glob("frame_*.jpg"))