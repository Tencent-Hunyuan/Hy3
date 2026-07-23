"""Terminal UI helpers for hy3-research CLI."""

from __future__ import annotations

import sys

# ANSI color codes
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

SEPARATOR = "─" * 60


def supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    if not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return True


def _c(code: str, text: str) -> str:
    """Apply color code if supported."""
    if supports_color():
        return f"{code}{text}{RESET}"
    return text


def print_header(text: str) -> None:
    """Print main title banner."""
    print()
    print(SEPARATOR)
    print(_c(BOLD + BLUE, text))
    print(SEPARATOR)
    print()


def print_stage(text: str) -> None:
    """Print stage indicator."""
    print(f"\n{_c(BOLD + CYAN, '▸')} {_c(BOLD, text)}")
    print(SEPARATOR)


def print_plan(plan: dict) -> None:
    """Display research plan to user."""
    print(_c(BOLD, f"\n研究主题: {plan.get('title', 'N/A')}"))
    print(_c(DIM, f"\n子主题 ({len(plan.get('subtopics', []))} 个):"))
    for i, st in enumerate(plan.get("subtopics", []), 1):
        print(f"  {i}. {st['query']}")
        print(f"     {_c(DIM, '核心问题: ' + st['key_question'])}")
    print(_c(DIM, f"\n报告大纲:"))
    for ol in plan.get("report_outline", []):
        print(f"  {ol}")
    print()


def print_sources(sources: list[dict]) -> None:
    """Display search results summary."""
    ok_count = sum(1 for s in sources if s.get("fetch_status", "ok") != "failed")
    print(_c(BOLD, f"\n来源 ({len(sources)} 条, {ok_count} 条可用):"))
    for s in sources[:15]:  # Show first 15
        status = _c(GREEN, "✓") if s.get("fetch_status", "ok") != "failed" else _c(RED, "✗")
        print(f"  [{s.get('index', '?')}] {status} {s.get('title', '')[:70]}")
        print(f"     {_c(DIM, s.get('url', '')[:80])}")
    if len(sources) > 15:
        print(f"  ... 还有 {len(sources) - 15} 条")
    print()


def print_synthesis_summary(syntheses: list[dict]) -> None:
    """Display synthesis progress summary."""
    print(_c(BOLD, f"\n综合完成 ({len(syntheses)} 个子主题):"))
    for s in syntheses:
        query = s["subtopic"]["query"]
        cited = len(s.get("cited_sources", []))
        text_len = len(s.get("synthesized_text", ""))
        print(f"  {_c(GREEN, '✓')} {query} — {cited} 引用, {text_len} 字符")
    print()


def print_report_summary(path: str, title: str) -> None:
    """Display report save confirmation."""
    print()
    print(SEPARATOR)
    print(_c(BOLD + GREEN, "✓ 报告生成完成!"))
    print(f"  标题: {title}")
    print(f"  路径: {path}")
    print(f"\n  查看报告: {_c(BOLD, f'python -m hy3research serve {path}')}")
    print(SEPARATOR)
    print()


def confirm(text: str, auto: bool = False) -> bool:
    """Ask user for confirmation. In auto mode, always returns True.

    Args:
        text: Confirmation prompt text.
        auto: If True, skip interaction and return True.

    Returns:
        True if confirmed, False otherwise.
    """
    if auto:
        print(f"{_c(DIM, '[auto]')} {text} → 是")
        return True
    try:
        answer = input(f"{text} [Y/n]: ").strip().lower()
        return answer in ("", "y", "yes")
    except (KeyboardInterrupt, EOFError):
        print()
        return False
