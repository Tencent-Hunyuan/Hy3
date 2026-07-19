"""Hy3 MCP Server — 本地 stdio，把读文件 + Hy3 推理封装成 MCP tools。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """从 server.py 同目录的 .env 加载环境变量（不覆盖已有值）。"""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    try:
        text = env_path.read_text(encoding="utf-8-sig")  # 兼容带 BOM 的记事本文件
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, val = line.partition("=")
        name = name.strip().lstrip("\ufeff")
        val = val.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = val


_load_dotenv()

from mcp.server.fastmcp import FastMCP
from openai import OpenAI

mcp = FastMCP(
    "hy3-code-assistant",
    instructions=(
        "本地代码助手：可列出/读取工作区文件，并用 Hy3 做代码评审或问答。"
        "调用 hy3_* 工具前请先用 read_file 或 list_dir 拿到上下文。"
    ),
)


def _workspace_root() -> Path:
    raw = os.environ.get("HY3_MCP_ROOT", os.getcwd())
    return Path(raw).expanduser().resolve()


def _safe_path(rel_or_abs: str) -> Path:
    """只允许访问 HY3_MCP_ROOT 目录内的文件。"""
    root = _workspace_root()
    p = Path(rel_or_abs).expanduser()
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    try:
        p.relative_to(root)
    except ValueError as e:
        raise ValueError(f"路径超出工作区 {root}: {p}") from e
    return p


def _hy3_client() -> tuple[OpenAI, str]:
    api_key = os.environ.get("HY3_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未设置环境变量 HY3_API_KEY")
    base_url = os.environ.get("HY3_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    model = os.environ.get("HY3_MODEL", "tencent/hy3:free")
    return OpenAI(api_key=api_key, base_url=base_url), model


def _chat(user_text: str, max_tokens: int = 2048) -> str:
    client, model = _hy3_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": user_text}],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


@mcp.tool()
def list_dir(path: str = ".") -> str:
    """列出工作区内某目录下的文件和子目录（名称、类型、大小）。

    Args:
        path: 相对工作区的目录路径，默认当前工作区根目录。
    """
    d = _safe_path(path)
    if not d.is_dir():
        return f"不是目录或不存在: {d}"
    lines = [f"工作区: {_workspace_root()}", f"目录: {d}", ""]
    entries = sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    for e in entries[:200]:
        kind = "dir " if e.is_dir() else "file"
        size = e.stat().st_size if e.is_file() else 0
        lines.append(f"{kind}\t{size:>10}\t{e.name}")
    if len(list(d.iterdir())) > 200:
        lines.append("... (仅显示前 200 项)")
    return "\n".join(lines)


@mcp.tool()
def read_file(path: str, max_chars: int = 30000) -> str:
    """读取工作区内的文本文件内容。

    Args:
        path: 相对工作区的文件路径。
        max_chars: 最多返回的字符数，默认 30000。
    """
    f = _safe_path(path)
    if not f.is_file():
        return f"文件不存在: {f}"
    text = f.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n... [截断，共 {len(text)} 字符]"
    return text


@mcp.tool()
def hy3_code_review(code: str, focus: str = "正确性、边界情况、可读性") -> str:
    """调用 Hy3 对给定代码做评审，输出问题列表与修改建议。

    Args:
        code: 待评审的源代码或 diff 文本。
        focus: 关注点，例如「安全」「性能」「风格」。
    """
    if not code.strip():
        return "code 为空"
    prompt = (
        f"请评审下列代码，关注：{focus}。\n"
        "用中文，分点写：1) 问题 2) 风险等级(高/中/低) 3) 修改建议。"
        "不要改写整份代码，除非必要只给小段示例。\n\n"
        f"```\n{code}\n```"
    )
    return _chat(prompt)


@mcp.tool()
def hy3_answer(question: str, context: str = "") -> str:
    """结合可选上下文，用 Hy3 回答关于代码或文档的问题。

    Args:
        question: 用户问题。
        context: 相关代码或文档片段；可先用 read_file 读入再填入。
    """
    if not question.strip():
        return "question 为空"
    if context.strip():
        prompt = f"基于下列上下文回答问题。用中文，简洁分点。\n\n上下文:\n{context}\n\n问题: {question}"
    else:
        prompt = f"用中文简洁回答:\n{question}"
    return _chat(prompt)


def main() -> None:
    # 默认 stdio，供 Cursor / Cline 等本地拉起
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
