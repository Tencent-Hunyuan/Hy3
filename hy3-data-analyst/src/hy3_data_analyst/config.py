"""Environment variable loading and validation.

API keys are loaded from a .env file (path overridable via HY3_ENV_FILE env var).
The server starts without requiring HY3_API_KEY; only ask_data checks for it.
"""

import os
from pathlib import Path


def _find_dotenv() -> Path | None:
    candidates = [
        Path(os.environ.get("HY3_ENV_FILE", "")),
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_dotenv() -> None:
    """Load .env file into os.environ. Does nothing if no .env found."""
    dotenv_path = _find_dotenv()
    if dotenv_path is None:
        return
    with open(dotenv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def get_hy3_api_key() -> str:
    key = os.environ.get("HY3_API_KEY", "")
    if not key:
        raise RuntimeError(
            "HY3_API_KEY 环境变量未设置。请在 .env 文件中配置 HY3_API_KEY=sk-你的密钥，"
            "或设置环境变量 HY3_API_KEY。\n"
            "HY3_API_KEY environment variable is not set. "
            "Please configure it in your .env file or export it."
        )
    return key


def get_hy3_base_url() -> str:
    return os.environ.get("HY3_BASE_URL", "https://openrouter.ai/api/v1")


def get_hy3_model() -> str:
    return os.environ.get("HY3_MODEL", "tencent/hy3:free")


def get_workspace_root() -> Path:
    root = os.environ.get("HY3_MCP_ROOT", "")
    if root:
        return Path(root).resolve()
    return Path.cwd()


# Load on import so other modules see the env vars
load_dotenv()
WORKSPACE_ROOT = get_workspace_root()
