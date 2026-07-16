# Hy3 Video Copilot

An AI-powered video editing assistant built with [Hy3](https://github.com/Tencent-Hunyuan/Hy3) — Tencent Hunyuan's hybrid reasoning MoE model.

## Hy3's Role

Hy3 acts as the **brain** of the application:
- Understands natural language editing instructions and generates structured editing plans
- Analyzes video metadata and provides professional editing suggestions
- Generates video scripts with shot-by-shot descriptions
- All intelligence flows through Hy3 API calls — no fine-tuning or local inference

## Features

| Feature | Description |
|---------|-------------|
| **Smart Edit** | Describe what you want in plain language → Hy3 generates a multi-step edit plan → executes with ffmpeg |
| **Video Analysis** | Upload a video → Hy3 analyzes metadata and provides improvement suggestions |
| **Script Generator** | Give a topic + style → Hy3 writes a complete video script with timing |

## Quick Start

### Prerequisites

- Python >= 3.10
- ffmpeg / ffprobe installed
- Hy3 API key

### Backend

```bash
cd hy3-video-copilot/backend
pip install -r requirements.txt
HY3_API_KEY=sk-xxx uvicorn main:app --reload --port 8000
```

### Frontend

Open `hy3-video-copilot/frontend/index.html` in your browser (or serve with any static server).

### End-to-End Demo

1. **Smart Edit Flow**: Upload a video → type "trim first 5 seconds and add fade-in" → watch the edited result
2. **Video Analysis Flow**: Upload a video → click "Analyze" → read Hy3's professional analysis

## Project Structure

```
hy3-video-copilot/
├── backend/
│   ├── main.py             # FastAPI server with 4 endpoints
│   ├── hy3_client.py       # Hy3 API wrapper
│   ├── video_processor.py  # ffmpeg-based video processing
│   └── requirements.txt
├── frontend/
│   └── index.html          # Single-page React UI
├── demo/                   # Demo GIFs
├── README.md
└── README_CN.md
```

## CodeBuddy Collaboration

The following code blocks were co-created with CodeBuddy:
- `backend/main.py` — API endpoint design and Hy3 prompt engineering
- `backend/video_processor.py` — ffmpeg command wrappers
- `frontend/index.html` — React UI component structure

## License

Apache-2.0
