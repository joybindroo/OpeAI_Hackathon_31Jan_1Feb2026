import tempfile
from pathlib import Path
from typing import Tuple
from openai import OpenAI
import pandas as pd

def transcribe_audio(client: OpenAI, audio_path: Path) -> Tuple[str, str]:
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
        )
    text = getattr(transcription, "text", "")
    language = getattr(transcription, "language", "")
    return text, language


def prepare_workspace() -> Path:
    workdir = Path(tempfile.mkdtemp(prefix="kids-video-eval-"))
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir

def analysis_to_table(analysis: dict) -> pd.DataFrame:
    rows = []
    for key, value in analysis.items():
        if isinstance(value, list):
            rows.append({
                "Category": key.replace("_", " ").title(),
                "Findings": "\n".join(f"- {v}" for v in value)
            })
        else:
            rows.append({
                "Category": key.replace("_", " ").title(),
                "Findings": str(value)
            })
    return pd.DataFrame(rows, index=range(1, len(rows) + 1))
