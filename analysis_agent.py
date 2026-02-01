"""Orchestrates multimodal reasoning with OpenAI guided by heuristics and rubric."""
import json
import re
from pathlib import Path
from typing import List, Dict
import base64

from openai import OpenAI

from heuristics import aggregate_heuristics
from rubric import (
    AI_SLOP_SIGNALS,
    BRAIN_ROT_SIGNALS,
    LEARNING_VALUE_SIGNALS,
    TWENTY_FIRST_CENTURY,
)


def chunk_transcript(transcript: str, chunk_words: int = 180) -> List[str]:
    words = transcript.split()
    if not words:
        return []
    return [" ".join(words[i : i + chunk_words]) for i in range(0, len(words), chunk_words)]


def build_chunk_notes(chunks: List[str]) -> List[str]:
    notes = []
    for idx, chunk in enumerate(chunks, start=1):
        preview = chunk[:200].replace("\n", " ")
        notes.append(f"Chunk {idx} (~{len(chunk.split())} words): {preview}")
    return notes


def extract_json(content: str) -> Dict:
    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        raise ValueError("Unable to find JSON in assistant response")
    return json.loads(match.group(0))



def encode_image_base64(image_path: Path) -> str:
    """
    Encode an image file as base64 for OpenAI vision models.
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")



def describe_video_frames(
    frame_paths: List[Path],
    client: OpenAI,
    model: str = "gpt-4o-mini",
) -> List[Dict]:
    """
    Uses a GPT vision-capable model to describe visual characteristics
    of sampled video frames relevant to educational quality for kids.

    Returns a list of dicts, one per frame, containing:
      - frame_path
      - visual_description
      - educational_relevance_notes
      - uncertainty_notes
    """

    results: List[Dict] = []

    system_prompt = (
        "You are assisting an automated reviewer of children's educational videos. "
        "Describe visuals cautiously. Avoid certainty. Focus on colors, visual clarity, "
        "stimulus level, readability, child-friendliness, and educational affordances. "
        "If unsure, explicitly state uncertainty."
    )
    print(f"Describing {len(frame_paths)} video frames using {model}...")
    for frame_path in frame_paths:
        image_b64 = encode_image_base64(frame_path)

        user_prompt = [
            {
                "type": "input_text",
                "text": ('''You assess the video frame image give to you for its suitability as children's educational content.'''
                ),
            },
            {
                "type": "input_image",
                "image_base64": image_b64,
            },
        ]

   
        response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                                           '''Describe only what is clearly visible in this frame that may affect its educational value for children.
Note dominant colors, visual clarity vs clutter, presence of readable text or symbols, apparent age suitability, and any obvious learning cues.
Avoid assumptions about intent or story. If uncertain, say so briefly. Respond in short concise bullet-like sentences.
'''
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                ],
            },
        ],
        temperature=0.3,
    )


        description_text = response.choices[0].message.content

        results.append(
            {
                "frame_path": str(frame_path),
                "visual_description": description_text.strip(),
                # "uncertainty_notes": (
                #     "Single-frame analysis; motion, narration, and context not visible."
                # ),
            }
        )
        print(f'"frame_path": {str(frame_path)},"visual_description": {description_text.strip()}')
        
    

    return results


# def run_analysis(
#     transcript: str,
#     duration: float,
#     language_hint: str,
#     frame_paths: List[Path],
#     client: OpenAI,
# ) -> Dict:

#     heuristics = aggregate_heuristics(transcript, duration, frame_paths)
#     chunks = chunk_transcript(transcript)
#     chunk_notes = build_chunk_notes(chunks)
#     rolling_summary = "\n".join(chunk_notes[-4:]) if chunk_notes else "No transcript available"

#     instructions = """
# You are a careful reviewer of children's educational content. Use the supplied heuristics, frames, and transcript fragments to evaluate the video with caution. This is an advisory tool for parents—avoid claiming certainty or diagnostics. Mention uncertainty explicitly. Base judgments on the provided rubric signals.
# Respond ONLY with JSON matching the requested schema without extra text or markdown.
# """

#     content_lines = [
#         f"Language hint: {language_hint or 'unspecified'}",
#         f"Duration (seconds): {duration:.1f}",
#         f"Heuristics: {json.dumps(heuristics)}",
#         f"Rolling summary: {rolling_summary}",
#         "Chunks:",
#     ]
#     content_lines.extend(chunk_notes)
#     content_lines.extend(
#         [
#             f"Frames sampled: {len(frame_paths)} (variance {heuristics['visual_variance']})",
#             f"Brain rot signals: {BRAIN_ROT_SIGNALS}",
#             f"Learning value signals: {LEARNING_VALUE_SIGNALS}",
#             f"21st century alignment: {TWENTY_FIRST_CENTURY}",
#             f"AI slop signals: {AI_SLOP_SIGNALS}",
#             instructions.strip(),
#             "Construct the result so that each array field contains a few short, cautious bullet-like strings. Highlight uncertainties explicitly.",
#             "If any rubric category cannot be assessed, note this in `uncertainties`.",
#         ]
#     )
#     content = "\n".join(content_lines)

#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[
#             {"role": "system", "content": "You evaluate kids' educational videos for cautious parents."},
#             {"role": "user", "content": content},
#         ],
#         temperature=0.3,
#     )

#     reply = response.choices[0].message.content
#     return extract_json(reply)




def run_analysis(
    transcript: str,
    duration: float,
    language_hint: str,
    frame_paths: List[Path],
    client: OpenAI,
) -> Dict:

    # 1. Deterministic heuristics (unchanged)
    heuristics = aggregate_heuristics(transcript, duration, frame_paths)

    # 2. Transcript chunking (unchanged)
    chunks = chunk_transcript(transcript)
    chunk_notes = build_chunk_notes(chunks)
    rolling_summary = "\n".join(chunk_notes[-4:]) if chunk_notes else "No transcript available"

    # 3. Vision-based frame descriptions
    frame_descriptions = describe_video_frames(
        frame_paths=frame_paths,
        client=client,
    )

    # Convert frame descriptions into prompt-friendly text
    visual_notes = []
    for idx, frame in enumerate(frame_descriptions, start=1):
        visual_notes.append(
            f"Frame {idx}: {frame.get('visual_description', '').strip()}\n"
            # f"Uncertainty: {frame.get('uncertainty_notes', '')}"
        )

    visual_summary = (
        "\n".join(visual_notes)
        if visual_notes
        else "No visual descriptions available."
    )

    # 4. Behavioral instructions
    instructions = """
You are a careful reviewer of children's educational content.
Use transcript fragments, visual frame descriptions, and heuristics together.
This is an advisory tool for parents—avoid claiming certainty or diagnostics.
Mention uncertainty explicitly, especially where single-frame visuals may mislead.
Base judgments strictly on the provided rubric signals.
Respond ONLY with JSON matching the requested schema without extra text or markdown and with Properly Capitalised Keys.
"""

    # 5. Prompt assembly
    content_lines = [
        f"Language hint: {language_hint or 'unspecified'}",
        f"Duration (seconds): {duration:.1f}",
        f"Heuristics: {json.dumps(heuristics)}",
        f"Frames sampled: {len(frame_paths)} (visual variance {heuristics['visual_variance']})",
        "",
        "Rolling transcript summary:",
        rolling_summary,
        "",
        "Transcript chunks:",
    ]

    content_lines.extend(chunk_notes)

    content_lines.extend(
        [
            "",
            "Visual frame descriptions (single-frame, limited context):",
            visual_summary,
            "",
            f"Brain rot signals: {BRAIN_ROT_SIGNALS}",
            f"Learning value signals: {LEARNING_VALUE_SIGNALS}",
            f"21st century alignment: {TWENTY_FIRST_CENTURY}",
            f"AI slop signals: {AI_SLOP_SIGNALS}",
            instructions.strip(),
            "Construct the result so that each array field contains a few short, cautious bullet-like strings.",
            "If any rubric category cannot be assessed, note this in `uncertainties`.",
        ]
    )

    content = "\n".join(content_lines)

    # 6. LLM call
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You evaluate kids' educational videos for cautious parents.",
            },
            {
                "role": "user",
                "content": content,
            },
        ],
        temperature=0.3,
    )

    reply = response.choices[0].message.content
    return extract_json(reply)
    

