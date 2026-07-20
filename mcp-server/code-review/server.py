"""
Code Review MCP Server — git diff 解析 + 混元 AI 代码评审。

MCP Tools:
  get_review_guide     — 返回代码评审的详细行为规范、提示词模板和工作流程
  get_diff_stats       — 项目目录树 + 变更文件清单
  get_file_content     — 获取文件内容（变更行带 diff 标注）
  review_with_hunyuan  — 与混元模型交互（服务端维护对话记忆）
  reset_review         — 清空混元对话记忆
"""

import argparse
import os
import sys
import signal
import logging

logging.getLogger("mcp").setLevel(logging.ERROR)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from tools.git_utils import (
    get_changed_files, get_file_diff, read_working_file, get_file_at_ref,
)
from tools.annotator import annotate_lines
from tools.assembler import (
    generate_project_tree, format_annotated_file, format_plain_file,
)
from tools.hy3_client import send_to_hunyuan, reset_conversation
from tools.tmp_store import (
    init_tmp, append_to_round, get_round_content, finish_round,
    clear_tmp, get_round_info,
)

mcp = FastMCP(
    name="code-review-hy3",
    instructions="""基于混元大模型的代码评审工具集。

角色: 你是管道，不是评审者。调用工具 → 拿到输出 → 原样传给混元。
混元决定一切：审核顺序、需要哪些文件、何时出评审。

开始评审前，务必先调用 get_review_guide 获取完整行为规范和提示词模板。""",
)


# ═══════════════════════════════════════════════════════════════════
# Tool 1: get_diff_stats
# ═══════════════════════════════════════════════════════════════════

@mcp.tool()
def get_diff_stats(project_root: str, base_branch: str = "main") -> str:
    """查看 git diff 变更文件清单和项目目录树。

    变更文件在目录树中标注 [ADDED]/[MODIFIED]/[DELETED]/[RENAMED]。

    Args:
        project_root: 项目根目录的绝对路径
        base_branch: 对比基准分支（默认 main）
    """
    if not os.path.isdir(project_root):
        return f"[ERROR] 项目目录不存在: {project_root}"

    raw = get_changed_files(project_root, base_branch)
    if not raw:
        return f"[INFO] 相对于 '{base_branch}' 未检测到文件变更"

    type_order = {"A": 0, "M": 1, "D": 2, "R": 3}
    raw.sort(key=lambda x: (type_order.get(x[1], 9), x[0]))

    changed_labels: dict[str, str] = {}
    for p, t, _ in raw:
        label_map = {"A": " [ADDED]", "M": " [MODIFIED]", "D": " [DELETED]", "R": " [RENAMED]"}
        changed_labels[p] = label_map.get(t, "")

    out: list[str] = []
    out.append("=" * 72)
    out.append("PROJECT TREE")
    out.append("=" * 72)
    out.append(generate_project_tree(project_root, changed_labels))
    out.append("")

    type_labels = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed"}
    markers = {"A": "+", "M": "~", "D": "-", "R": "→"}

    out.append("=" * 72)
    out.append("CHANGED FILES")
    out.append("=" * 72)
    for p, t, old in raw:
        label = type_labels.get(t, t)
        marker = markers.get(t, "?")
        note = f"  ← {old}" if old else ""
        out.append(f"  {marker} [{label:8s}] {p}{note}")

    out.append("=" * 72)
    out.append(f"  Total: {len(raw)} files")
    out.append("")
    out.append("Tip: 用 get_file_content 读取变更文件的详细内容")
    return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════
# Tool 2: get_file_content
# ═══════════════════════════════════════════════════════════════════

# 单文件大小上限（字节）。拦截 go.sum / lock / __pycache__ 等无意义大文件。
_MAX_FILE_BYTES = 200 * 1024  # 200 KB


@mcp.tool()
def get_file_content(
    project_root: str,
    file_path: str,
    base_branch: str = "main",
) -> str:
    """读取文件内容，暂存到服务端 tmp 目录。返回简短摘要，不返回文件内容。

    同一轮评审中多次调用会追加写入同一个 tmp 文件。
    后续调用 review_with_hunyuan(use_tmp=True) 将 tmp 文件内容发给混元。
    超过大小上限（默认 200KB）的文件会直接失败，避免拉取无意义大文件。

    Args:
        project_root: 项目根目录的绝对路径
        file_path: 相对于 project_root 的文件路径
        base_branch: 对比基准分支（默认 main）
    """
    if not os.path.isdir(project_root):
        return f"[ERROR] 项目目录不存在: {project_root}"

    full_path = os.path.normpath(os.path.join(project_root, file_path))
    if not full_path.startswith(os.path.normpath(project_root)):
        return f"[ERROR] 文件路径越权: {file_path}"

    if not os.path.isfile(full_path):
        content = get_file_at_ref(project_root, file_path, "HEAD")
        if content is None:
            return f"[ERROR] 文件不存在: {file_path}"
        size = len(content.encode("utf-8"))
        if size > _MAX_FILE_BYTES:
            return (
                f"[ERROR] 文件过大 ({size} bytes > {_MAX_FILE_BYTES} bytes): {file_path}\n"
                f"跳过无意义大文件，请选择源码文件。"
            )
        formatted = f"### {file_path} [FILE DELETED]\n\n{format_plain_file(content)}"
    else:
        try:
            size = os.path.getsize(full_path)
        except OSError:
            return f"[ERROR] 无法读取文件: {file_path}"
        if size > _MAX_FILE_BYTES:
            return (
                f"[ERROR] 文件过大 ({size} bytes > {_MAX_FILE_BYTES} bytes): {file_path}\n"
                f"跳过 go.sum / lock / 二进制等无意义大文件，请选择源码文件。"
            )

        content = read_working_file(project_root, file_path)
        if content is None:
            return f"[ERROR] 无法读取文件: {file_path}"

        diff = get_file_diff(project_root, file_path, base_branch)
        if diff:
            annotated_lines = annotate_lines(content, diff)
            if annotated_lines:
                formatted = f"### {file_path}\n\n{format_annotated_file(annotated_lines)}"
            else:
                formatted = f"### {file_path}\n\n{format_plain_file(content)}"
        else:
            formatted = f"### {file_path}\n\n{format_plain_file(content)}"

    # ── 存入 tmp，不返回内容 ──
    append_to_round(formatted)
    info = get_round_info()

    return f"[OK] 已暂存到 Round {info['round']} | {file_path} | 文件: {info['file']}"


# ═══════════════════════════════════════════════════════════════════
# Tool 3: review_with_hunyuan
# ═══════════════════════════════════════════════════════════════════

@mcp.tool()
def review_with_hunyuan(content: str = "", use_tmp: bool = False) -> str:
    """将内容发给混元，返回混元的自然语言响应。服务端自动维护对话记忆。

    两种模式:
      1. content 模式 (默认): 将 content 参数原样发给混元
      2. use_tmp 模式: 读取当前轮的 tmp 文件内容发给混元，发完后自动进入下一轮

    Args:
        content: 发给混元的消息（use_tmp=False 时使用）
        use_tmp: True 则读取 tmp 文件内容发给混元，发完后自动 advance 到下一轮
    """
    try:
        if use_tmp:
            tmp_content = get_round_content()
            if tmp_content is None:
                return "[ERROR] 没有暂存文件。请先调用 get_file_content 读取文件。"
            reply = send_to_hunyuan(tmp_content)
            finish_round()  # 本轮回合结束，下一轮 get_file_content 会写新文件
            return reply
        else:
            return send_to_hunyuan(content)
    except RuntimeError as e:
        return f"[ERROR] {e}"
    except Exception as e:
        return f"[ERROR] 评审过程出错: {e}"


# ═══════════════════════════════════════════════════════════════════
# Tool 4: reset_review
# ═══════════════════════════════════════════════════════════════════

@mcp.tool()
def reset_review(clear_temp_files: bool = True) -> str:
    """清空混元对话记忆和临时文件，开始新一轮代码评审。

    Args:
        clear_temp_files: 是否清空临时文件（默认 True）
    """
    reset_conversation()
    if clear_temp_files:
        clear_tmp()
    return "[OK] 对话记忆和临时文件已清空"


# ═══════════════════════════════════════════════════════════════════
# Tool 5: get_review_guide
# ═══════════════════════════════════════════════════════════════════

@mcp.tool()
def get_review_guide() -> str:
    """返回代码评审的详细行为规范、提示词模板和工作流程。

    在开始任何代码评审之前，先调用本工具获取完整的 Agent 行为规范。
    包含: 禁止行为清单、精确的提示词模板、异常处理规则。
    """
    guide_path = os.path.join(os.path.dirname(__file__), "prompts", "code_review_system.md")
    try:
        with open(guide_path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, FileNotFoundError):
        return "[ERROR] 行为规范文件未找到"


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hy3 Code Review MCP Server")
    parser.add_argument(
        "--transport", default="sse",
        choices=["sse", "streamable-http"],
        help="传输协议 (默认 sse)"
    )
    parser.add_argument("--port", type=int, default=8000, help="SSE/HTTP 端口 (默认 8000)")
    parser.add_argument("--host", default="127.0.0.1", help="SSE/HTTP 监听地址 (默认 127.0.0.1)")
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    print(f"Code Review MCP Server → http://{args.host}:{args.port}/sse", file=sys.stderr)

    # 优雅关闭：Ctrl+C 不打印 asyncio traceback
    signal.signal(signal.SIGINT, lambda _s, _f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda _s, _f: sys.exit(0))

    init_tmp()
    try:
        mcp.run(transport=args.transport)
    except KeyboardInterrupt:
        pass
