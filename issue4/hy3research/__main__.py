"""CLI entry point for hy3-research: deep research assistant."""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from hy3research import __version__
from hy3research.client import get_client
from hy3research.config import Config
from hy3research.planner import generate_plan
from hy3research.searcher import search_all
from hy3research.fetcher import fetch_all
from hy3research.synthesizer import synthesize_all
from hy3research.reporter import generate_report, save_report
from hy3research.ui import (
    print_header,
    print_stage,
    print_plan,
    print_sources,
    print_synthesis_summary,
    print_report_summary,
    confirm,
    _c,
    BOLD,
    GREEN,
    RED,
    BLUE,
    DIM,
    RESET,
)
from hy3research.server import serve_report


def _slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:50]


def _output_dir(topic: str, base: str | None = None) -> str:
    """Generate output directory path."""
    root = Path(base) if base else Path("outputs")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slugify(topic)
    return str(root / f"{slug}-{timestamp}")


def cmd_research(args: argparse.Namespace) -> None:
    """Run the research pipeline."""
    topic = args.topic
    auto = args.auto
    mock = args.mock

    print_header(f"🔬 hy3-research v{__version__}")
    print(f"  主题: {_c(BOLD, topic)}")
    print(f"  模式: {'自动' if auto else '交互'}{' (mock)' if mock else ''}")
    print()

    # Verify client works
    if not mock and Config.is_mock:
        print(_c("", "⚠️  未配置 HY3_API_KEY，自动切换到 mock 模式\n"))
        mock = True

    # ── Stage 1: Plan ──
    print_stage("阶段 1/5: 生成研究计划")
    plan = generate_plan(topic, mock=mock)
    print_plan(plan)

    if not confirm("计划是否可行？", auto=auto):
        print("已取消。")
        return

    if not auto:
        print("可编辑计划（直接回车跳过）:")
        try:
            new_title = input(f"  标题 [{plan['title']}]: ").strip()
            if new_title:
                plan["title"] = new_title
        except (KeyboardInterrupt, EOFError):
            return

    # ── Stage 2: Search ──
    print_stage("阶段 2/5: 并行搜索")
    sources = search_all(plan["subtopics"], mock=mock)
    print_sources(sources)

    if not sources:
        print(_c(RED, "❌ 搜索无结果。请检查网络或搜索配置。"))
        return

    if confirm("是否继续抓取内容？", auto=auto):
        # ── Stage 3: Fetch ──
        print_stage("阶段 3/5: 抓取源内容")
        fetched = fetch_all(sources, mock=mock)
    else:
        print("已取消抓取。使用已有摘要信息进行综合...")
        fetched = []  # skip fetch, proceed with snippets only
    ok_count = sum(1 for f in fetched if f["fetch_status"] == "ok")
    failed_count = sum(1 for f in fetched if f["fetch_status"] == "failed")
    print(f"  抓取结果: {_c(GREEN, str(ok_count) + ' 成功')}, {_c(RED, str(failed_count) + ' 失败')}")
    print_sources(fetched)

    # ── Stage 4: Synthesize ──
    print_stage("阶段 4/5: 综合材料 (Hy3)")
    syntheses = synthesize_all(plan["subtopics"], sources, fetched, mock=mock)
    print_synthesis_summary(syntheses)

    if not confirm("是否生成最终报告？", auto=auto):
        print("已取消。综合材料已保留在内存中。")
        return

    # ── Stage 5: Report ──
    print_stage("阶段 5/5: 生成报告 (Hy3)")
    report_md = generate_report(
        plan["title"],
        plan["report_outline"],
        syntheses,
        sources,
        mock=mock,
    )

    output_dir = _output_dir(topic, args.output)
    save_report(report_md, output_dir, plan["title"], plan, sources)
    print_report_summary(output_dir, plan["title"])

    # Auto-serve if --serve flag
    if args.serve:
        port = Config.HY3_RESEARCH_PORT
        print(f"\n启动Web服务...")
        serve_report(output_dir, port=port)


def cmd_serve(args: argparse.Namespace) -> None:
    """Serve an existing report directory."""
    port = args.port or Config.HY3_RESEARCH_PORT
    serve_report(args.directory, port=port)


def cmd_plan(args: argparse.Namespace) -> None:
    """Only generate and display research plan."""
    topic = args.topic
    mock = args.mock
    if not mock and Config.is_mock:
        mock = True
        print(_c("", "⚠️  未配置 HY3_API_KEY，自动切换到 mock 模式\n"))
    print_header(f"🔬 hy3-research v{__version__} — 仅规划模式")
    plan = generate_plan(topic, mock=mock)
    print_plan(plan)


def _build_research_parser() -> argparse.ArgumentParser:
    """Build parser for the default research command (no subcommands)."""
    parser = argparse.ArgumentParser(
        prog="hy3research",
        description="hy3-research: 基于 Hy3 的深度研究助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"hy3-research {__version__}"
    )
    parser.add_argument("topic", help="研究主题")
    parser.add_argument("--auto", action="store_true", help="自动模式，无需交互确认")
    parser.add_argument("--mock", action="store_true", help="Mock 离线演示模式")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--serve", "-s", action="store_true", help="完成后自动启动Web服务")
    parser.add_argument("--plan-only", action="store_true", help="仅生成并显示研究计划")
    return parser


def _build_main_parser() -> argparse.ArgumentParser:
    """Build parser with subcommands for serve/plan routing and help display."""
    parser = argparse.ArgumentParser(
        prog="hy3research",
        description="hy3-research: 基于 Hy3 的深度研究助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  hy3research "量子计算在药物研发中的应用"        # 交互模式
  hy3research --auto "AI芯片发展趋势"               # 自动模式
  hy3research --mock "测试主题"                     # Mock 离线演示
  hy3research --plan-only "主题"                    # 仅规划
  hy3research serve outputs/report/                 # 启动Web服务
  hy3research serve outputs/report/ --port 8080     # 自定义端口
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"hy3-research {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")
    serve_parser = subparsers.add_parser("serve", help="启动Web报告服务")
    serve_parser.add_argument("directory", help="报告目录路径")
    serve_parser.add_argument("--port", type=int, help="服务端口 (默认 8899)")
    serve_parser.set_defaults(func=cmd_serve)
    plan_parser = subparsers.add_parser("plan", help="仅生成研究计划")
    plan_parser.add_argument("topic", help="研究主题")
    plan_parser.add_argument("--mock", action="store_true", help="使用 mock 模式")
    plan_parser.set_defaults(func=cmd_plan)
    return parser


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) == 1:
        _build_main_parser().print_help()
        return

    # Detect if first positional arg is a known subcommand
    first_pos = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            first_pos = arg
            break

    if first_pos == "serve":
        parser = _build_main_parser()
        args = parser.parse_args()
        cmd_serve(args)
    elif first_pos == "plan":
        parser = _build_main_parser()
        args = parser.parse_args()
        cmd_plan(args)
    else:
        # Default: research command
        parser = _build_research_parser()
        args = parser.parse_args()

        if args.plan_only:
            cmd_plan(args)
        elif args.topic:
            cmd_research(args)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
