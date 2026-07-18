"""
Configuration for Hy3 RAG - Multi-document RAG Q&A System.
All settings can be overridden via environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

if not os.getenv("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
UPLOAD_DIR = DATA_DIR / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend"

CHROMA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Hy3 API ────────────────────────────────────────────────
HY3_API_BASE = os.getenv("HY3_API_BASE", "https://tokenhub.tencentmaas.com/v1")
HY3_API_KEY = os.getenv("HY3_API_KEY", "")
HY3_MODEL = os.getenv("HY3_MODEL", "hy3")
HY3_TIMEOUT = int(os.getenv("HY3_TIMEOUT", "120"))

# ── Embedding ──────────────────────────────────────────────
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

# ── Chunking ───────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

# ── Retrieval ──────────────────────────────────────────────
TOP_K_CHUNKS = int(os.getenv("TOP_K_CHUNKS", "6"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "true").lower() == "true"
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "32000"))

# ── Supported document formats ─────────────────────────────
SUPPORTED_FORMATS = {
    '.pdf': 'PDF Document',
    '.txt': 'Text File',
    '.md': 'Markdown',
    '.docx': 'Word Document',
    '.doc': 'Legacy Word Document',
    '.rst': 'reStructuredText',
    '.py': 'Python Source',
    '.js': 'JavaScript Source',
    '.ts': 'TypeScript Source',
    '.json': 'JSON Data',
    '.csv': 'CSV Data',
    '.xml': 'XML Data',
    '.html': 'HTML Document',
    '.htm': 'HTML Document',
}

# ── Server ─────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8766"))
