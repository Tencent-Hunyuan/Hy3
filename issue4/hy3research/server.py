"""HTTP static file server for viewing research reports in browser."""

from __future__ import annotations

import http.server
import os
import socket
import webbrowser
from pathlib import Path
from hy3research.ui import print_header, _c, BOLD, GREEN, CYAN, RESET


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def serve_report(report_dir: str, port: int = 8899, open_browser: bool = True) -> None:
    """Serve a report directory over HTTP and optionally open browser.

    Args:
        report_dir: Path to directory containing report.md and report.html.
        port: Port to listen on.
        open_browser: Whether to auto-open browser.
    """
    report_path = Path(report_dir).resolve()

    if not report_path.is_dir():
        print(f"错误: 目录不存在 — {report_path}")
        return

    report_md = report_path / "report.md"
    if not report_md.is_file():
        print(f"警告: 未找到 report.md — {report_md}")

    # If report.html or index.html doesn't exist, generate from template
    report_html = report_path / "report.html"
    index_html = report_path / "index.html"
    if not report_html.is_file() or not index_html.is_file():
        _generate_html(report_path)

    os.chdir(str(report_path))

    handler = http.server.SimpleHTTPRequestHandler

    print_header(f"🌐 hy3-research 报告服务")
    print(f"  目录: {report_path}")
    print(f"  地址: {_c(BOLD + GREEN, f'http://localhost:{port}')}")
    print(f"  按 {_c(BOLD, 'Ctrl+C')} 停止服务")
    print()

    if open_browser:
        webbrowser.open(f"http://localhost:{port}")

    try:
        with http.server.HTTPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except socket.error as e:
        # Port already in use
        print(f"{_c('', '端口 {port} 被占用')}: {e}")
    except KeyboardInterrupt:
        print(f"\n{_c(BOLD + GREEN, '✓')} 服务已停止")


def _generate_html(report_dir: Path) -> None:
    """Generate report.html from template with embedded markdown content."""
    template_path = TEMPLATE_DIR / "report.html"
    report_md = report_dir / "report.md"

    if not template_path.is_file():
        print(f"警告: 模板文件不存在 — {template_path}")
        return

    template = template_path.read_text(encoding="utf-8")

    if report_md.is_file():
        md_content = report_md.read_text(encoding="utf-8")
        # Escape for JS string
        md_escaped = md_content.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        html = template.replace("__REPORT_MARKDOWN__", md_escaped).replace("__REPORT_TITLE__", report_dir.name)
    else:
        html = template.replace("__REPORT_MARKDOWN__", "# 报告未找到").replace("__REPORT_TITLE__", report_dir.name)

    (report_dir / "report.html").write_text(html, encoding="utf-8")
    (report_dir / "index.html").write_text(html, encoding="utf-8")  # Also serve as default page
