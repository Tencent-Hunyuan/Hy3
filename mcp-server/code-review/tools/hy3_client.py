"""
Hy3 API 客户端 — Chat Completions API + 本地对话历史。
"""

import os
from openai import OpenAI
from dotenv import load_dotenv


env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
env_path = os.path.normpath(env_path)
load_dotenv(dotenv_path=env_path, override=False)


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("HY3_API_KEY") or os.environ.get("hy3_api_key") or ""
        base_url = (
            os.environ.get("HY3_BASE_URL")
            or os.environ.get("hy3_base_url")
            or "https://tokenhub.tencentmaas.com/v1"
        )
        if not api_key:
            raise RuntimeError("HY3_API_KEY 环境变量未设置（请检查 .env 文件）")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


# ═══════════════════════════════════════════════════════════════════
# 对话历史（本地维护）
# ═══════════════════════════════════════════════════════════════════

_messages: list = []  


# ═══════════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════════

def send_to_hunyuan(content: str) -> str:
    """将内容发给混元，自动继承之前的对话历史。

    本地维护 messages 列表，每次发送完整历史。
    """
    global _messages
    client = _get_client()

    _messages.append({"role": "user", "content": content})

    response = client.chat.completions.create(
        model="hy3",
        messages=_messages,  
    )

    reply = response.choices[0].message.content or ""
    _messages.append({"role": "assistant", "content": reply})
    return reply


def reset_conversation() -> None:
    """清空对话历史。"""
    global _messages
    _messages.clear()


