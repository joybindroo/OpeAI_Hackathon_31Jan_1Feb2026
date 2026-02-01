# streamlit_app.py
import streamlit as st
import json
import os
import tempfile
from pathlib import Path
from typing import Tuple

from openai import OpenAI

from analysis_agent import run_analysis
from video_utils import (
    download_youtube,
    extract_audio,
    sample_frames,
    get_video_duration,
)
import pandas as pd

from helpers import (transcribe_audio, prepare_workspace, analysis_to_table)
# ---------- Helper functions ----------

# def analysis_to_table(analysis: dict) -> pd.DataFrame:
#     rows = []
#     for key, value in analysis.items():
#         if isinstance(value, list):
#             rows.append({
#                 "Category": key.replace("_", " ").title(),
#                 "Findings": "\n".join(f"- {v}" for v in value)
#             })
#         else:
#             rows.append({
#                 "Category": key.replace("_", " ").title(),
#                 "Findings": str(value)
#             })
#     return pd.DataFrame(rows, index=range(1, len(rows) + 1))







# def transcribe_audio(client: OpenAI, audio_path: Path) -> Tuple[str, str]:
#     with open(audio_path, "rb") as audio_file:
#         transcription = client.audio.transcriptions.create(
#             model="gpt-4o-transcribe",
#             file=audio_file,
#         )
#     return (
#         getattr(transcription, "text", ""),
#         getattr(transcription, "language", ""),
#     )


# def prepare_workspace() -> Path:
#     workdir = Path(tempfile.mkdtemp(prefix="kids-video-eval-"))
#     workdir.mkdir(parents=True, exist_ok=True)
#     return workdir


# ---------- Streamlit UI ----------

st.set_page_config(
    page_title="Kids Educational Video Evaluator",
    layout="wide",
)

st.title("🎓 Kids Educational Video Quality Evaluator")
st.caption(
    "Advisory tool for parents. Uses transcript, visuals, and heuristics — "
    "not a diagnostic system."
)

# ---------- Sidebar ----------
st.sidebar.header("Configuration")

api_key = st.sidebar.text_input(
    "OpenAI API Key",
    type="password",
)

frames = st.sidebar.slider(
    "Frames to sample",
    min_value=3,
    max_value=10,
    value=5,
)

input_mode = st.sidebar.radio(
    "Video Source",
    ["YouTube URL", "Upload Local Video"],
)

youtube_url = None
uploaded_file = None

if input_mode == "YouTube URL":
    youtube_url = st.sidebar.text_input(
        "Public YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
    )
else:
    uploaded_file = st.sidebar.file_uploader(
        "Upload short video",
        type=["mp4", "mov", "mkv"],
    )

run_btn = st.sidebar.button("▶ Run Evaluation", type="primary")


# ---------- Main Execution ----------
if run_btn:
    if not api_key:
        st.error("OpenAI API key is required.")
        st.stop()

    if input_mode == "YouTube URL" and not youtube_url:
        st.error("Please provide a YouTube URL.")
        st.stop()

    if input_mode == "Upload Local Video" and not uploaded_file:
        st.error("Please upload a video file.")
        st.stop()

    os.environ["OPENAI_API_KEY"] = api_key
    client = OpenAI(api_key=api_key)

    workspace = prepare_workspace()

    # ---- UI placeholders ----
    progress = st.progress(0)
    log_box = st.empty()
    logs = []

    def log(msg: str):
        logs.append(msg)
        log_box.markdown(
            "### 🧾 Execution Log\n" + "\n".join(f"- {l}" for l in logs)
        )

    try:
        progress.progress(5)
        log("Workspace created")

        # --- Video acquisition ---
        if input_mode == "YouTube URL":
            log("Downloading YouTube video")
            video_path = download_youtube(youtube_url, workspace)
        else:
            log("Saving uploaded video")
            video_path = workspace / uploaded_file.name
            with open(video_path, "wb") as f:
                f.write(uploaded_file.read())

        progress.progress(20)
        log("Video ready")

        # --- Processing ---
        log("Reading video duration")
        duration = get_video_duration(video_path)

        progress.progress(30)
        log("Extracting audio")
        audio_path = workspace / "audio.wav"
        extract_audio(video_path, audio_path)

        progress.progress(45)
        log("Transcribing audio")
        transcript, language = transcribe_audio(client, audio_path)

        progress.progress(60)
        log(f"Transcription complete (language: {language or 'unknown'})")

        with st.expander("📝 Transcript preview", expanded=False):
            st.text_area(
                label="",
                value=transcript[:3000],
                height=200,
            )

        log("Sampling video frames")
        frames_dir = workspace / "frames"
        frame_paths = sample_frames(video_path, frames_dir, max_frames=frames)

        progress.progress(75)
        log(f"Sampled {len(frame_paths)} frames")

        # --- Analysis ---
        log("Running multimodal analysis")
        analysis = run_analysis(
            transcript=transcript,
            duration=duration,
            language_hint=language,
            frame_paths=frame_paths,
            client=client,
        )

        progress.progress(100)
        log("Analysis complete")

        # ---------- Output UI ----------
        st.success("✅ Evaluation completed")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📊 Evaluation Result")
            # st.table(analysis)
            # st.json(analysis)
            # st.html(analysis)
            st.table(analysis_to_table(analysis))


        with col2:
            st.subheader("⬇️ Download Report")
            st.download_button(
                "Download JSON",
                data=json.dumps(analysis, indent=2, ensure_ascii=False),
                file_name="video_evaluation.json",
                mime="application/json",
            )

    except Exception as exc:
        progress.progress(100)
        log(f"❌ Analysis failed: {exc}")
        st.error(str(exc))
