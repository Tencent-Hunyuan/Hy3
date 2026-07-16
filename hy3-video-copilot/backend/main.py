import os
import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from hy3_client import Hy3Client
from video_processor import VideoProcessor

app = FastAPI(title="Hy3 Video Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hy3 = Hy3Client()
vp = VideoProcessor()

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT_EDIT = """你是一个视频剪辑专家助手。根据用户的自然语言描述，生成可执行的视频剪辑计划。

请返回严格的 JSON 格式（无 markdown 包裹）：
{
  "plan": "用中文描述你的编辑计划",
  "commands": [
    {
      "action": "trim|fade_in|fade_out|speed|concat|extract_frame|extract_audio",
      "params": {}
    }
  ]
}

支持的 action 及参数：
- trim: {"start": float(秒), "duration": float(秒)}
- fade_in: {"duration": float(秒)}
- fade_out: {"duration": float(秒)}
- speed: {"factor": float(倍速)}
- extract_frame: {"time": float(秒)}
- extract_audio: {}
- concat: {} (合并多个片段)

请确保 param 值是数字而非字符串。"""

SYSTEM_PROMPT_ANALYZE = """你是一个视频内容分析专家。分析提供的视频元数据，生成详细的分析报告。
包含：视频基本信息、场景推测、剪辑建议、可能的改进方向。"""


@app.post("/api/chat")
async def chat(message: str = Form(...), reasoning: str = Form("no_think")):
    response = hy3.chat(
        messages=[{"role": "user", "content": message}],
        reasoning_effort=reasoning,
    )
    return {"response": response}


@app.post("/api/edit")
async def edit_video(
    file: UploadFile = File(...),
    instruction: str = Form(...),
):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())

    metadata = vp.get_metadata(str(file_path))
    metadata_text = json.dumps(metadata, indent=2, ensure_ascii=False)
    plan_text = f"视频元数据:\n{metadata_text}\n\n用户指令: {instruction}"

    response = hy3.chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_EDIT},
            {"role": "user", "content": plan_text},
        ],
        reasoning_effort="high",
    )

    try:
        plan = json.loads(response.strip().removeprefix("```json").removesuffix("```").strip())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Hy3 返回了无效 JSON: {response}")

    output_dir = OUTPUT_DIR / file.filename.rsplit(".", 1)[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    current_input = str(file_path)

    for i, cmd in enumerate(plan.get("commands", [])):
        action = cmd["action"]
        params = cmd.get("params", {})
        ext = file.filename.rsplit(".", 1)[1] if "." in file.filename else "mp4"
        output_path = str(output_dir / f"step_{i:02d}_{action}.{ext}")

        if action == "trim":
            current_input = vp.trim(current_input, params["start"], params["duration"], output_path)
        elif action == "fade_in":
            current_input = vp.fade_in(current_input, params["duration"], output_path)
        elif action == "fade_out":
            current_input = vp.fade_out(current_input, params["duration"], output_path)
        elif action == "speed":
            current_input = vp.speed(current_input, params["factor"], output_path)
        elif action == "extract_frame":
            img_path = str(output_dir / f"frame_{params['time']}.jpg")
            vp.extract_frame(current_input, params["time"], img_path)
            current_input = current_input
        elif action == "extract_audio":
            audio_path = str(output_dir / "audio.mp3")
            vp.extract_audio(current_input, audio_path)
            current_input = current_input

    return {
        "plan": plan["plan"],
        "output": current_input,
        "steps": len(plan.get("commands", [])),
    }


@app.post("/api/analyze")
async def analyze_video(
    file: UploadFile = File(...),
):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())

    metadata = vp.get_metadata(str(file_path))
    metadata_text = json.dumps(metadata, indent=2, ensure_ascii=False)

    response = hy3.chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_ANALYZE},
            {"role": "user", "content": f"请分析以下视频信息:\n{metadata_text}"},
        ],
        reasoning_effort="high",
    )

    return {"analysis": response}


@app.post("/api/script")
async def generate_script(
    topic: str = Form(...),
    duration: float = Form(60.0),
    style: str = Form("通用"),
):
    prompt = f"""请为以下主题生成一个视频脚本，时长约{duration}秒，风格：{style}。

主题：{topic}

请按时间线组织，包含：画面描述、旁白/台词、建议时长。返回 JSON 格式。"""

    response = hy3.chat(
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="high",
    )

    return {"script": response}


@app.get("/api/output/{filename:path}")
async def get_output(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(str(file_path))
