#!/usr/bin/env python3
"""
Hy3 Code Reviewer — 基于腾讯混元 Hy3 推理能力的 CLI 代码审查工具。

使用方式:
    # 审查单个文件
    python hy3_review.py path/to/file.py

    # 审查多个文件
    python hy3_review.py src/*.py

    # 指定推理强度
    python hy3_review.py app.py --effort high

    # JSON 格式输出
    python hy3_review.py app.py --output json

    # 保存审查报告
    python hy3_review.py app.py --output report.md

前置条件:
    1. 在 showcase/ 目录下复制 .env.example 为 .env 并填入 HY3_API_KEY
    2. pip install "openai>=1.0.0" python-dotenv
"""

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)

BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3-preview")

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".sql", ".html", ".css",
    ".yaml", ".yml", ".toml", ".json", ".xml", ".md",
}

# ── 审查 Prompt 模板 ──────────────────────────────────

REVIEW_SYSTEM_PROMPT = textwrap.dedent("""\
你是一位资深代码审查专家。请对以下代码进行全面审查，输出结构化报告。

审查维度：
1. Bug 风险 — 逻辑错误、空值处理、边界条件、异常处理
2. 安全漏洞 — SQL注入、XSS、不安全反序列化、硬编码密钥、路径遍历
3. 性能问题 — 不必要循环、内存泄漏、N+1查询、低效数据结构
4. 代码质量 — 命名规范、函数长度、复杂度、重复代码、类型安全
5. 最佳实践 — 设计模式、SOLID原则、错误处理、文档完整性

输出格式要求：
- 每个问题使用以下格式：`[严重度] 文件名:行号 — 问题描述 — 修复建议`
- 严重度分为：🔴 严重、🟡 警告、🔵 建议
- 最后给出总体评分（1-10分）和一句话总结

代码文件如下。""")

REVIEW_USER_TEMPLATE = """请审查以下代码文件。

文件路径：{file_path}
编程语言：{language}

```{language}
{code}
```

请给出完整的结构化审查报告。"""


def detect_language(file_path: str) -> str:
    """根据文件扩展名检测编程语言。"""
    ext_to_lang = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "bash",
        ".bash": "bash",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".json": "json",
        ".xml": "xml",
        ".md": "markdown",
    }
    ext = Path(file_path).suffix.lower()
    return ext_to_lang.get(ext, "text")


def review_file(client: OpenAI, file_path: str, effort: str = "high") -> dict:
    """审查单个文件，返回结构化结果。"""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return {"error": f"不支持的文件类型: {ext}"}

    try:
        code = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": f"无法读取文件（编码问题）: {file_path}"}

    language = detect_language(file_path)
    user_message = REVIEW_USER_TEMPLATE.format(
        file_path=file_path,
        language=language,
        code=code,
    )

    params = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
        "extra_body": {
            "chat_template_kwargs": {"reasoning_effort": effort},
        },
    }

    response = client.chat.completions.create(**params)
    choice = response.choices[0]

    return {
        "file": file_path,
        "language": language,
        "lines": code.count("\n") + 1,
        "review": choice.message.content,
        "reasoning": getattr(choice.message, "reasoning_content", None),
        "finish_reason": choice.finish_reason,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        },
    }


def format_text_output(results: list[dict]) -> str:
    """格式化文本输出。"""
    lines = []
    separator = "=" * 72
    total_tokens = 0

    for i, result in enumerate(results):
        if "error" in result:
            lines.append(f"❌ {result['error']}")
            continue

        lines.append(separator)
        lines.append(f"📄 文件 {i + 1}/{len(results)}: {result['file']}")
        lines.append(f"   语言: {result['language']} | 行数: {result['lines']} | "
                     f"Tokens: {result['usage']['total_tokens']}")
        lines.append(separator)

        if result.get("reasoning"):
            lines.append("")
            lines.append("🧠 推理过程:")
            lines.append("-" * 40)
            lines.append(result["reasoning"][:500])
            lines.append("")

        lines.append("📋 审查报告:")
        lines.append("-" * 40)
        lines.append(result["review"])
        lines.append("")
        lines.append(f"完成原因: {result['finish_reason']}")
        lines.append("")

        total_tokens += result["usage"]["total_tokens"]

    lines.append(separator)
    lines.append(f"📊 总计: {len(results)} 个文件, {total_tokens} tokens")
    lines.append(separator)

    return "\n".join(lines)


def format_json_output(results: list[dict]) -> str:
    """格式化 JSON 输出。"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "total_files": len(results),
        "total_tokens": sum(r.get("usage", {}).get("total_tokens", 0) for r in results),
        "results": results,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def format_markdown_output(results: list[dict]) -> str:
    """格式化 Markdown 输出。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Hy3 Code Review Report",
        f"",
        f"**生成时间**: {now}  ",
        f"**模型**: {MODEL}  ",
        f"**文件数**: {len(results)}  ",
        f"**总 Tokens**: {sum(r.get('usage', {}).get('total_tokens', 0) for r in results)}",
        f"",
        "---",
        "",
    ]

    for i, result in enumerate(results):
        if "error" in result:
            lines.append(f"## ❌ {result['error']}")
            lines.append("")
            continue

        lines.append(f"## 📄 {Path(result['file']).name}")
        lines.append("")
        lines.append(f"- **路径**: `{result['file']}`")
        lines.append(f"- **语言**: {result['language']}")
        lines.append(f"- **行数**: {result['lines']}")
        lines.append(f"- **Tokens**: {result['usage']['total_tokens']}")
        lines.append("")

        if result.get("reasoning"):
            lines.append("### 🧠 推理过程")
            lines.append("")
            lines.append("```")
            lines.append(result["reasoning"][:800])
            lines.append("```")
            lines.append("")

        lines.append("### 📋 审查报告")
        lines.append("")
        lines.append(result["review"])
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Hy3 Code Reviewer — 基于腾讯混元 Hy3 的 CLI 代码审查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        示例:
          python hy3_review.py app.py
          python hy3_review.py src/*.py --effort low
          python hy3_review.py main.go utils.go --output json
          python hy3_review.py src/ --output report.md
          python hy3_review.py app.py --output result.json
        """),
    )
    parser.add_argument(
        "files", nargs="+",
        help="要审查的文件路径（支持通配符和目录）",
    )
    parser.add_argument(
        "--effort", "-e",
        choices=["no_think", "low", "high"],
        default="high",
        help="推理强度: no_think (快速) / low (轻度) / high (深度) [默认: high]",
    )
    parser.add_argument(
        "--output", "-o",
        default="text",
        help="输出格式: text (终端显示) / json (保存为 .json 文件) / 指定路径如 report.md 或 result.json",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="覆盖默认模型 (默认: 使用 .env 中的 HY3_MODEL)",
    )
    return parser.parse_args()


def collect_files(paths: list[str]) -> list[str]:
    """收集所有需要审查的文件。"""
    files = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                for f in path.rglob(f"*{ext}"):
                    if f.is_file():
                        files.append(str(f))
        elif path.is_file():
            files.append(str(path))
        else:
            # 尝试 glob 匹配
            from glob import glob
            matched = glob(p)
            for m in matched:
                if os.path.isfile(m):
                    files.append(m)

    # 去重排序
    return sorted(set(files))


def main():
    global MODEL

    args = parse_args()

    if not API_KEY:
        print("=" * 60, file=sys.stderr)
        print("❌ 错误: 未设置 HY3_API_KEY", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)
        print("请复制 .env.example 为 .env 并填入你的 API Key:", file=sys.stderr)
        print(f"  cd {Path(__file__).resolve().parent}", file=sys.stderr)
        print("  copy .env.example .env", file=sys.stderr)
        print("  # 编辑 .env，填入 HY3_API_KEY=sk-xxx", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    model = args.model or MODEL

    MODEL = model

    files = collect_files(args.files)
    if not files:
        print("❌ 未找到匹配的文件", file=sys.stderr)
        sys.exit(1)

    # 进度信息始终输出到 stderr，保持 stdout 干净供 pipe 使用
    info = sys.stderr
    print(f"🔍 Hy3 Code Reviewer", file=info)
    print(f"   模型: {model} | 推理强度: {args.effort}", file=info)
    print(f"   待审查文件: {len(files)} 个", file=info)
    print(file=info)

    results = []
    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] 审查中: {file_path} ...", end=" ", flush=True, file=info)
        result = review_file(client, file_path, effort=args.effort)
        if "error" in result:
            print(f"❌ {result['error']}", file=info)
        else:
            print(f"✓ ({result['usage']['total_tokens']} tokens)", file=info)
        results.append(result)

    print(file=info)

    # 输出结果
    if args.output == "json" or args.output.endswith(".json"):
        # JSON 文件输出 — 中文直接写入文件，避免终端 \uXXXX 转义
        if args.output == "json":
            output_path = f"hy3_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            output_path = args.output
        Path(output_path).write_text(format_json_output(results), encoding="utf-8")
        print(f"📝 JSON 报告已保存至: {output_path}", file=info)
    elif args.output.endswith(".md"):
        md_content = format_markdown_output(results)
        output_path = args.output
        Path(output_path).write_text(md_content, encoding="utf-8")
        print(f"📝 Markdown 报告已保存至: {output_path}", file=info)
        print(file=info)
        print(md_content)
    else:
        print(format_text_output(results))


if __name__ == "__main__":
    main()
