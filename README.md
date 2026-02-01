# Kids Educational Video Quality Evaluation Agent 

Evaluates short children's educational videos using OpenAI's multimodal stack plus lightweight heuristics.


## Notes
- The agent analyzes a children’s educational video. 
- You can upload your own video (mp4 etc.) or provide it with a publicly accessible Youtube Video URL. 
- It starts by first downloading the video file,
- Then transcribing the audio ("gpt-4o-transcribe"), 
- Sampling a few representative frames, and
- Extracting visual information ("gpt-4o-mini"). 
- Calculates light-weight heuristics (non LLM). lik
  - word_repetition_ratio
  - speaking_speed
  - transcript_density, and
  - visual_variance (pixel level)
- It then combines these signals with the transcript to assess 
  - visual & speech patterns, 
  - learning value, 
  - potential overstimulation, and 
  - content quality using a 
  - structured rubric. 
- The output is a table with concise advisory bullet points, intended to help parents understand the educational strengths and limitations of the video, while explicitly noting uncertainty.
- All findings are advisory; no claims of diagnosis or certification.



## Setup
1. Install system requirements: `ffmpeg`, `yt-dlp` (available via apt/brew).
2. Create a Python environment and install deps:
   ```
   pip install -r requirements.txt
   ```
3. Export your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```



## Running
```bash
python3 app.py --api-key api_proj...   --video sample_v1.mp4
or
python3 app.py --api-key api-proj...   --youtube https://www.youtube.com/shorts/ZA9J9Tx17RE
```
### Command line arguments available:
--youtube, YouTube URL to evaluate
--video, Path to a short local video file (mp4 etc)
--api-key, OpenAI API key (falls back to OPENAI_API_KEY env variable)
--frames, Number of frames to sample

### For Streamlit based UI
```bash
streamlit run streamlit_app.py

```

## Sample output (JSON):
```json
{
  "educational_value": [
    "Uncertain due to minimal content",
    "Potential for vocabulary building with single word",
    "Lacks clear learning goal"
  ],
  "engagement_level": [
    "Uncertain due to short duration",
    "Fast cuts may cause overstimulation",
    "Minimal content limits engagement"
  ],
  "suitability_for_age": [
    "Uncertain due to lack of context",
    "Single word may suit very young children",
    "No inappropriate content detected"
  ],
  "cultural_sensitivity": [
    "Uncertain due to lack of context",
    "No cultural references detected",
    "Minimal content limits assessment"
  ],
  "uncertainties": [
    "Very short duration limits assessment",
    "Single word provides little context",
    "Lack of clear learning objective"
  ]
}

```
