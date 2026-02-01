"""Lightweight, non-LLM heuristic helpers."""
from pathlib import Path
import re
from typing import List
from PIL import Image

def word_repetition_ratio(text: str) -> float:
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    unique = len(set(words))
    return max(0.0, 1 - unique / len(words))


def speaking_speed(word_count: int, duration: float) -> float:
    if duration <= 0:
        return 0.0
    return word_count / duration


def transcript_density(word_count: int, duration: float) -> float:
    if duration <= 0:
        return 0.0
    return word_count / duration


def compute_visual_variance(frame_paths: List[Path]) -> float:
    if len(frame_paths) < 2:
        return 0.0

    averages = []
    for path in frame_paths:
        try:
            with Image.open(path) as img:
                grayscale = img.convert("L")
                pixels = list(grayscale.getdata())
                if not pixels:
                    continue
                averages.append(sum(pixels) / len(pixels))
        except Exception:
            continue

    if len(averages) < 2:
        return 0.0

    diffs = [abs(averages[i] - averages[i - 1]) for i in range(1, len(averages))]
    return sum(diffs) / len(diffs)


def aggregate_heuristics(transcript: str, duration: float, frame_paths: List[Path]) -> dict:
    word_count = len(re.findall(r"\b\w+\b", transcript))
    return {
        "word_count": word_count,
        "duration_seconds": duration,
        "repetition_ratio": round(word_repetition_ratio(transcript), 4),
        "speaking_speed_wps": round(speaking_speed(word_count, duration), 2),
        "transcript_density_wps": round(transcript_density(word_count, duration), 2),
        "visual_variance": round(compute_visual_variance(frame_paths), 2),
    }
