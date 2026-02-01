"""Entry point for the Kids Educational Video Quality Evaluation Agent."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Tuple

from openai import OpenAI

from analysis_agent import run_analysis
from video_utils import download_youtube, extract_audio, sample_frames, get_video_duration
from helpers import transcribe_audio, prepare_workspace, analysis_to_table


# def transcribe_audio(client: OpenAI, audio_path: Path) -> Tuple[str, str]:
#     with open(audio_path, "rb") as audio_file:
#         transcription = client.audio.transcriptions.create(
#             model="gpt-4o-transcribe",
#             file=audio_file,
#         )
#     text = getattr(transcription, "text", "")
#     language = getattr(transcription, "language", "")
#     return text, language


# def prepare_workspace() -> Path:
#     workdir = Path(tempfile.mkdtemp(prefix="kids-video-eval-"))
#     workdir.mkdir(parents=True, exist_ok=True)
#     return workdir


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate kids educational videos via multimodal heuristics.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--youtube", help="YouTube URL to evaluate")
    group.add_argument("--video", help="Path to a short local video file (mp4 etc)")
    parser.add_argument("--api-key", help="OpenAI API key (falls back to OPENAI_API_KEY env variable)")
    parser.add_argument("--frames", type=int, default=5, help="Number of frames to sample")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("missing OpenAI API key; set --api-key or OPENAI_API_KEY")
        sys.exit(1)

    workspace = prepare_workspace()
    client = OpenAI(api_key=api_key)

    if args.youtube:
        video_path = download_youtube(args.youtube, workspace)
    else:
        candidate = Path(args.video)
        if not candidate.exists():
            print(f"video file does not exist: {candidate}")
            sys.exit(1)
        video_path = candidate

    duration = get_video_duration(video_path)
    audio_path = workspace / "audio.wav"
    extract_audio(video_path, audio_path)
    print(f"Extracted audio to {audio_path}")
    print('Transcribing audio...')
    transcript, language = transcribe_audio(client, audio_path)
    print(f"Transcription complete (language: {language})\n Text: {transcript}")

    frames_dir = workspace / "frames"
    print('Sampling frames...')
    frame_paths = sample_frames(video_path, frames_dir, max_frames=args.frames)
    print(f"Sampled {len(frame_paths)} frames to {frames_dir}")

    try:
        analysis = run_analysis(
            transcript=transcript,
            duration=duration,
            language_hint=language,
            frame_paths=frame_paths,
            client=client,
        )
    except Exception as exc:
        print(f"analysis failed: {exc}")
        sys.exit(1)

    print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
