"""
Memory manager - persists documents, folders, and conversations to disk.

All state lives under data/memory/ as JSON so it survives restarts.
DocumentMemory tracks which documents are loaded and which folder they belong
to. FolderManager handles folder CRUD and moving documents between folders.
ConversationMemory stores chat history per conversation id.
"""
import json
import logging
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional

import config

logger = logging.getLogger(__name__)

MEMORY_DIR = config.DATA_DIR / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_FILE = MEMORY_DIR / "documents.json"
FOLDERS_FILE = MEMORY_DIR / "folders.json"
CONVERSATIONS_DIR = MEMORY_DIR / "conversations"
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return default


def _save(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class DocumentMemory:
    def __init__(self):
        self._docs: List[Dict] = _load(DOCUMENTS_FILE, [])

    def get_all(self) -> List[Dict]:
        return self._docs

    def get_by_folder(self, folder_id: Optional[str]) -> List[Dict]:
        if not folder_id:
            return [d for d in self._docs if not d.get("folder_id")]
        return [d for d in self._docs if d.get("folder_id") == folder_id]

    def get(self, filename: str) -> Optional[Dict]:
        for d in self._docs:
            if d["filename"] == filename:
                return d
        return None

    def add(self, filename: str, folder_id: Optional[str], chunk_count: int, file_type: str):
        existing = self.get(filename)
        if existing:
            existing["folder_id"] = folder_id
            existing["chunk_count"] = chunk_count
            existing["file_type"] = file_type
        else:
            self._docs.append(
                {
                    "filename": filename,
                    "folder_id": folder_id,
                    "chunk_count": chunk_count,
                    "file_type": file_type,
                }
            )
        self._save()

    def remove(self, filename: str):
        self._docs = [d for d in self._docs if d["filename"] != filename]
        self._save()

    def set_folder(self, filename: str, folder_id: Optional[str]):
        d = self.get(filename)
        if d:
            d["folder_id"] = folder_id
            self._save()

    def sync_with_store(self, store):
        """Bidirectional sync: reflect what's actually in the vector store."""
        try:
            store_docs = store.get_all_documents()
        except Exception as e:
            logger.warning("sync_with_store failed: %s", e)
            return
        store_names = {d["filename"] for d in store_docs}
        # Remove docs no longer in the store
        self._docs = [d for d in self._docs if d["filename"] in store_names]
        # Add docs present in store but missing from memory
        known = {d["filename"] for d in self._docs}
        for d in store_docs:
            if d["filename"] not in known:
                self._docs.append(
                    {
                        "filename": d["filename"],
                        "folder_id": None,
                        "chunk_count": d["chunk_count"],
                        "file_type": "",
                    }
                )
        self._save()

    def _save(self):
        _save(DOCUMENTS_FILE, self._docs)


class FolderManager:
    def __init__(self):
        self._folders: List[Dict] = _load(FOLDERS_FILE, [])

    def list_folders(self) -> List[Dict]:
        return self._folders

    def get(self, folder_id: str) -> Optional[Dict]:
        for f in self._folders:
            if f["id"] == folder_id:
                return f
        return None

    def create(self, name: str) -> Dict:
        folder = {"id": uuid.uuid4().hex[:8], "name": name}
        self._folders.append(folder)
        self._save()
        return folder

    def delete(self, folder_id: str):
        self._folders = [f for f in self._folders if f["id"] != folder_id]
        # Unassign documents that were in this folder
        doc_memory.remove_folder(folder_id)
        self._save()

    def rename(self, folder_id: str, name: str):
        f = self.get(folder_id)
        if f:
            f["name"] = name
            self._save()

    def move_doc(self, filename: str, folder_id: Optional[str]):
        doc_memory.set_folder(filename, folder_id)

    def _save(self):
        _save(FOLDERS_FILE, self._folders)


class ConversationMemory:
    def __init__(self):
        self._index: Dict[str, Dict] = {}
        for p in CONVERSATIONS_DIR.glob("*.json"):
            data = _load(p, None)
            if data and "id" in data:
                self._index[data["id"]] = data

    def list(self) -> List[Dict]:
        items = sorted(
            self._index.values(),
            key=lambda c: c.get("updated_at", 0),
            reverse=True,
        )
        return [
            {
                "id": c["id"],
                "title": c.get("title", "新对话"),
                "updated_at": c.get("updated_at", 0),
            }
            for c in items
        ]

    def create(self) -> Dict:
        conv_id = uuid.uuid4().hex
        conv = {
            "id": conv_id,
            "title": "新对话",
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._index[conv_id] = conv
        self._persist(conv)
        return conv

    def get(self, conv_id: str) -> Optional[Dict]:
        return self._index.get(conv_id)

    def delete(self, conv_id: str):
        if conv_id in self._index:
            del self._index[conv_id]
        path = CONVERSATIONS_DIR / f"{conv_id}.json"
        if path.exists():
            path.unlink()

    def add_message(self, conv_id: str, role: str, content: str):
        conv = self._index.get(conv_id)
        if not conv:
            conv = self.create()
            conv_id = conv["id"]
        conv["messages"].append({"role": role, "content": content})
        conv["updated_at"] = time.time()
        # Auto-title from the first user message
        if conv["title"] == "新对话" and role == "user":
            conv["title"] = content[:30] + ("…" if len(content) > 30 else "")
        self._persist(conv)
        return conv_id

    def rename(self, conv_id: str, title: str):
        conv = self._index.get(conv_id)
        if conv:
            conv["title"] = title
            self._persist(conv)

    def _persist(self, conv: Dict):
        path = CONVERSATIONS_DIR / f"{conv['id']}.json"
        _save(path, conv)


# Cross-manager helpers
_doc_memory = DocumentMemory()
_folder_manager = FolderManager()


def _patch_doc_memory():
    """Give FolderManager access to DocumentMemory for unassigning docs."""
    global _doc_memory

    def _remove_folder(folder_id):
        for d in _doc_memory.get_all():
            if d.get("folder_id") == folder_id:
                d["folder_id"] = None
        _doc_memory._save()

    FolderManager.remove_folder = _remove_folder


_patch_doc_memory()

# Public singletons
doc_memory = _doc_memory
folder_manager = _folder_manager
conversation_memory = ConversationMemory()
