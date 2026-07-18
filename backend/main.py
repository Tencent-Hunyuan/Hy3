"""
FastAPI application for Hy3 RAG.

Exposes document upload/parsing, vector search, streaming Q&A (SSE),
folder management, and conversation persistence. Serves the static
frontend from /frontend.
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from document_parser import parse_document
from text_chunker import chunk_text
from vector_store import VectorStore
from rag_engine import RAGEngine
from memory_manager import doc_memory, folder_manager, conversation_memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hy3_rag")

app = FastAPI(title="Hy3 RAG", version="2.0.0")

# ── Core services ──────────────────────────────────────────
store = VectorStore()
rag = RAGEngine(store)

# Sync persisted document memory with the actual vector store on boot.
doc_memory.sync_with_store(store)


# ── Request models ──────────────────────────────────────────
class QARequest(BaseModel):
    question: str
    top_k: Optional[int] = None
    conversation_id: Optional[str] = None
    folder_id: Optional[str] = None
    source_filters: Optional[List[str]] = None


# ── Helpers ─────────────────────────────────────────────────
def _resolve_source_filters(
    folder_id: Optional[str], explicit_docs: Optional[List[str]]
) -> Optional[List[str]]:
    """Union of a folder's documents and explicitly named documents."""
    names = set()
    if folder_id:
        for d in doc_memory.get_by_folder(folder_id):
            names.add(d["filename"])
    if explicit_docs:
        names.update(explicit_docs)
    return list(names) if names else None


def _build_history(conversation_id: Optional[str]):
    if not conversation_id:
        return []
    conv = conversation_memory.get(conversation_id)
    if not conv:
        return []
    msgs = conv.get("messages", [])
    # Keep only the last MAX_HISTORY_TURNS exchanges.
    trimmed = msgs[-config.MAX_HISTORY_TURNS * 2:]
    return [
        {"role": m["role"], "content": m["content"]}
        for m in trimmed
        if m["role"] in ("user", "assistant")
    ]


# ── Health & stats ──────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok" if config.HY3_API_KEY else "no_api_key",
        "documents": len(doc_memory.get_all()),
        "chunks": store.count(),
        "model": config.HY3_MODEL,
    }


@app.get("/api/documents/stats")
async def stats():
    return {"documents": len(doc_memory.get_all()), "chunks": store.count()}


# ── Documents ───────────────────────────────────────────────
@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "unnamed"
    ext = Path(filename).suffix.lower()
    if ext not in config.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式: {ext}。支持: {', '.join(config.SUPPORTED_FORMATS)}",
        )

    dest = config.UPLOAD_DIR / filename
    content = await file.read()
    dest.write_bytes(content)

    try:
        text, meta = parse_document(str(dest))
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"解析失败: {e}")

    chunks = chunk_text(text, doc_name=filename)
    if not chunks:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="文档内容为空或无法分块")

    store.add_documents(chunks)
    doc_memory.add(filename, None, len(chunks), meta.get("file_type", ext))
    logger.info("Uploaded %s -> %d chunks", filename, len(chunks))
    return {
        "filename": filename,
        "chunk_count": len(chunks),
        "file_type": meta.get("file_type"),
        "size_bytes": meta.get("size_bytes"),
    }


@app.get("/api/documents")
async def list_documents(folder_id: Optional[str] = None, include_all: bool = False):
    if include_all:
        docs = doc_memory.get_all()
    else:
        docs = doc_memory.get_by_folder(folder_id)
    return {"documents": docs, "total": len(docs)}


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    store.delete_document(filename)
    doc_memory.remove(filename)
    # Also remove the uploaded file
    f = config.UPLOAD_DIR / filename
    if f.exists():
        f.unlink(missing_ok=True)
    return {"deleted": filename}


# ── Q&A (streaming) ─────────────────────────────────────────
@app.post("/api/qa/stream")
async def qa_stream(req: QARequest):
    source_filters = _resolve_source_filters(req.folder_id, req.source_filters)
    history = _build_history(req.conversation_id)

    async def event_stream():
        try:
            async for ev in rag.answer_stream(
                query=req.question,
                top_k=req.top_k or config.TOP_K_CHUNKS,
                conversation_history=history,
                source_filters=source_filters,
            ):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/qa/chat")
async def qa_chat(req: QARequest):
    """Conversation-aware streaming Q&A that persists messages."""
    # Ensure a conversation exists
    conv_id = req.conversation_id or conversation_memory.create()["id"]
    conversation_memory.add_message(conv_id, "user", req.question)

    source_filters = _resolve_source_filters(req.folder_id, req.source_filters)
    history = _build_history(conv_id)

    async def event_stream():
        answer_parts = []
        try:
            async for ev in rag.answer_stream(
                query=req.question,
                top_k=req.top_k or config.TOP_K_CHUNKS,
                conversation_history=history,
                source_filters=source_filters,
            ):
                if ev.get("type") == "done":
                    answer_parts.append(ev.get("answer", ""))
                elif ev.get("type") == "token":
                    answer_parts.append(ev.get("content", ""))
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        full = "".join(answer_parts)
        conversation_memory.add_message(conv_id, "assistant", full)
        # Emit the conversation id so the client can persist it.
        yield f"data: {json.dumps({'type': 'conversation', 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Folders ─────────────────────────────────────────────────
@app.get("/api/folders")
async def get_folders():
    return {"folders": folder_manager.list_folders()}


@app.post("/api/folders")
async def create_folder(name: str = Form(...)):
    folder = folder_manager.create(name)
    return {"folder": folder}


@app.delete("/api/folders/{folder_id}")
async def delete_folder(folder_id: str):
    folder_manager.delete(folder_id)
    return {"deleted": folder_id}


@app.post("/api/folders/{folder_id}/documents")
async def move_document_to_folder(folder_id: str, filename: str = Form(...)):
    if folder_id != "none":
        folder = folder_manager.get(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
    target = None if folder_id == "none" else folder_id
    doc_memory.set_folder(filename, target)
    return {"filename": filename, "folder_id": target}


# ── Conversations ───────────────────────────────────────────
@app.get("/api/conversations")
async def list_conversations():
    return {"conversations": conversation_memory.list()}


@app.post("/api/conversations")
async def create_conversation():
    conv = conversation_memory.create()
    return {"conversation": conv}


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = conversation_memory.get(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"conversation": conv}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    conversation_memory.delete(conv_id)
    return {"deleted": conv_id}


@app.post("/api/conversations/{conv_id}/messages")
async def add_conversation_message(conv_id: str, role: str = Form(...), content: str = Form(...)):
    conversation_memory.add_message(conv_id, role, content)
    return {"ok": True}


# ── Static frontend ─────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


# Serve the static frontend assets. index.html references /static/app.js and
# /static/styles.css, so mount the frontend directory at /static (not at /,
# otherwise /static/* would resolve to frontend/static/* which does not exist).
app.mount("/static", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")
