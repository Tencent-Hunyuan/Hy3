"""通过已安装的 MCP stdio server 运行固定知识库评测。"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import time
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

RUNTIME_ENV_NAMES = {
    "COMSPEC",
    "HOME",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
}
HY3_ENV_NAMES = {
    "HY3_API_KEY",
    "HY3_BASE_URL",
    "HY3_ENDPOINT_PROFILE",
    "HY3_KB_CHUNK_CHARS",
    "HY3_KB_CHUNK_OVERLAP_CHARS",
    "HY3_KB_MAX_CONTEXT_CHARS",
    "HY3_KB_MAX_DISCOVERY_DEPTH",
    "HY3_KB_MAX_DISCOVERY_DIRECTORIES",
    "HY3_KB_MAX_DISCOVERY_ENTRIES",
    "HY3_KB_MAX_FILE_BYTES",
    "HY3_KB_MAX_FILES_PER_RUN",
    "HY3_KB_MAX_PDF_PAGES",
    "HY3_KB_MAX_TOTAL_BYTES_PER_RUN",
    "HY3_KB_MAX_SUMMARY_REQUESTS",
    "HY3_KB_PROMPT_RESERVE_CHARS",
    "HY3_MAX_OUTPUT_TOKENS",
    "HY3_MAX_RETRIES",
    "HY3_MODEL",
    "HY3_REASONING_EFFORT",
    "HY3_TIMEOUT_SECONDS",
}
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class EvalFailure(RuntimeError):
    """表示不携带 server 原始输出的安全评测失败。"""


@dataclass(frozen=True)
class EvalCase:
    """一个固定问题、期望答案与声明来源。"""

    question: str
    answer: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class EvalMetadata:
    """仅包含允许写入评测报告的运行元数据。"""

    model: str
    endpoint_profile: str
    reasoning_effort: str
    package_version: str
    git_commit: str
    corpus_sha256: str
    endpoint_host: str
    timestamp_utc: datetime
    search_limit: int
    ask_top_k: int


@dataclass(frozen=True)
class EvalRow:
    """单个问题的可审计评测结果。"""

    number: int
    question: str
    expected_answer: str
    actual_answer: str
    declared_sources: tuple[str, ...]
    search_sources: tuple[str, ...]
    citation_sources: tuple[str, ...]
    duration_seconds: float
    passed: bool
    failure: str


def parse_evaluation(path: Path) -> tuple[EvalCase, ...]:
    """解析并严格校验固定 XML 评测文件。"""
    try:
        root = ElementTree.parse(path).getroot()
        pairs = root.findall("qa_pair")
        if root.tag != "evaluation" or len(pairs) != 10:
            raise ValueError

        cases = []
        seen_questions: set[str] = set()
        for pair in pairs:
            question = pair.findtext("question", "").strip()
            answer = pair.findtext("answer", "").strip()
            if not question or question in seen_questions or not answer:
                raise ValueError
            seen_questions.add(question)

            sources = []
            for source_element in pair.findall("source"):
                source = _normalize_declared_source(source_element.text or "")
                if source in sources:
                    raise ValueError
                sources.append(source)
            if not sources:
                raise ValueError
            cases.append(EvalCase(question=question, answer=answer, sources=tuple(sources)))
    except (ElementTree.ParseError, OSError, UnicodeError, ValueError):
        raise EvalFailure("invalid evaluation fixture") from None
    return tuple(cases)


def _normalize_declared_source(value: str) -> str:
    """校验并规范化评测声明的相对 POSIX 来源路径。"""
    source = value.strip()
    if (
        not source
        or "\\" in source
        or any(ord(character) < 32 or ord(character) == 127 for character in source)
    ):
        raise ValueError
    raw_parts = source.split("/")
    if any(part in {".", ".."} for part in raw_parts):
        raise ValueError
    first_part = next((part for part in raw_parts if part), "")
    if len(first_part) >= 2 and first_part[0].isalpha() and first_part[1] == ":":
        raise ValueError
    normalized = PurePosixPath(source)
    if normalized.is_absolute() or not normalized.parts:
        raise ValueError
    return normalized.as_posix()


def build_child_environment(
    parent: Mapping[str, str],
    knowledge_root: Path,
    storage_dir: Path,
) -> dict[str, str]:
    """构造 live server 的最小环境并强制隔离知识根与索引目录。"""
    child: dict[str, str] = {}
    for key, value in parent.items():
        normalized = key.upper()
        if normalized in RUNTIME_ENV_NAMES | HY3_ENV_NAMES:
            child[normalized] = value
    child.update(
        {
            "PYTHONUTF8": "1",
            "PYTHON_DOTENV_DISABLED": "1",
            "HY3_KB_ROOTS": os.fspath(knowledge_root.resolve()),
            "HY3_KB_STORAGE_DIR": os.fspath(storage_dir.resolve()),
        }
    )
    return child


def safe_endpoint_host(base_url: str) -> str:
    """只返回无凭据、无路径与查询参数的 HTTP(S) endpoint host。"""
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError:
        return "unavailable"
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        return "unavailable"
    hostname = parsed.hostname
    if ":" in hostname:
        hostname = f"[{hostname}]"
    return f"{hostname}:{port}" if port is not None else hostname


def corpus_sha256(root: Path) -> str:
    """基于相对路径和文件字节计算可复现语料摘要。"""
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _prepare_output(output: Path) -> None:
    """创建报告父目录并移除既有普通文件或符号链接。"""
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.is_symlink() or output.is_file():
            output.unlink()
        elif output.exists():
            raise EvalFailure("report output is not a file")
    except (OSError, ValueError):
        raise EvalFailure("report output preparation failed") from None


def _atomic_write_text(output: Path, text: str) -> None:
    """在目标目录完整落盘 UTF-8 临时文件后原子替换报告。"""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, output)
    except (OSError, UnicodeError, ValueError):
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
        with suppress(OSError):
            if output.is_symlink() or output.is_file():
                output.unlink()
        raise EvalFailure("report write failed") from None


def _missing_suffixes(
    declared_sources: Sequence[str],
    actual_sources: Sequence[str],
) -> tuple[str, ...]:
    return tuple(
        source
        for source in declared_sources
        if not any(_source_matches_suffix(actual, source) for actual in actual_sources)
    )


def _source_matches_suffix(actual_source: str, declared_source: str) -> bool:
    """按完整 POSIX 路径组件判断来源后缀。"""
    actual_parts = PurePosixPath(actual_source.replace("\\", "/")).parts
    declared_parts = PurePosixPath(declared_source).parts
    return len(actual_parts) >= len(declared_parts) and (
        actual_parts[-len(declared_parts) :] == declared_parts
    )


def evaluate_row(
    *,
    number: int,
    question: str,
    expected_answer: str,
    declared_sources: tuple[str, ...],
    search_sources: tuple[str, ...],
    actual_answer: str | None,
    citation_sources: tuple[str, ...],
    duration_seconds: float,
) -> EvalRow:
    """按检索、答案和引用顺序判定单行结果。"""
    missing_search = _missing_suffixes(declared_sources, search_sources)
    if missing_search:
        failure = "retrieval preflight missing: " + ", ".join(missing_search)
        normalized_answer = "not called"
    else:
        normalized_answer = actual_answer if actual_answer is not None else "not called"
        missing_citations = _missing_suffixes(declared_sources, citation_sources)
        if actual_answer is None:
            failure = "answer call failed"
        elif actual_answer.strip().casefold() != expected_answer.strip().casefold():
            failure = "answer mismatch"
        elif missing_citations:
            failure = "citation coverage missing: " + ", ".join(missing_citations)
        else:
            failure = ""
    return EvalRow(
        number=number,
        question=question,
        expected_answer=expected_answer,
        actual_answer=normalized_answer,
        declared_sources=declared_sources,
        search_sources=search_sources,
        citation_sources=citation_sources,
        duration_seconds=duration_seconds,
        passed=not failure,
        failure=failure,
    )


def _cell(value: str) -> str:
    """将任意文本限制为安全的单行 Markdown 表格单元格。"""
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _source_labels(source_paths: Sequence[str]) -> str:
    """把来源路径缩减为去重文件名, 避免报告泄露目录。"""
    labels = []
    for source_path in source_paths:
        label = PurePosixPath(source_path.replace("\\", "/")).name
        if label and label not in labels:
            labels.append(label)
    return ", ".join(labels)


def _timestamp(value: datetime) -> str:
    """将时区感知时间规范化为秒级 UTC 字符串。"""
    utc_value = value.astimezone(timezone.utc).replace(microsecond=0)
    return utc_value.isoformat().replace("+00:00", "Z")


def render_report(metadata: EvalMetadata, rows: Sequence[EvalRow]) -> str:
    """渲染只含允许元数据和来源后缀的实测报告。"""
    passed = sum(row.passed for row in rows)
    total = len(rows)
    percentage = (passed / total * 100) if total else 0.0
    lines = [
        "# Hy3 Knowledge Base MCP Evaluation",
        "",
        f"- Model: {metadata.model}",
        f"- Endpoint profile: {metadata.endpoint_profile}",
        f"- Reasoning effort: {metadata.reasoning_effort}",
        f"- Package version: {metadata.package_version}",
        f"- Git commit: {metadata.git_commit}",
        f"- Corpus SHA-256: {metadata.corpus_sha256}",
        "- Transport: stdio",
        "- Corpus: examples/knowledge_base",
        f"- Questions: {total}",
        f"- Endpoint host: {metadata.endpoint_host}",
        f"- UTC timestamp: {_timestamp(metadata.timestamp_utc)}",
        f"- Retrieval: search limit {metadata.search_limit}; ask top-k {metadata.ask_top_k}",
        f"- Score: {passed}/{total} ({percentage:.1f}%)",
        "",
        "| # | Result | Duration (s) | Question | Expected | Actual | Sources "
        "| Search hits | Citations | Failure |",
        "|---:|:---:|---:|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.number),
                    "PASS" if row.passed else "FAIL",
                    f"{row.duration_seconds:.3f}",
                    _cell(row.question),
                    _cell(row.expected_answer),
                    _cell(row.actual_answer),
                    _cell(", ".join(row.declared_sources)),
                    _cell(_source_labels(row.search_sources)),
                    _cell(_source_labels(row.citation_sources)),
                    _cell(row.failure),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _tool_payload(result: Any, tool_name: str) -> dict[str, Any]:
    """提取成功工具调用的结构化载荷。"""
    if result.isError or not isinstance(result.structuredContent, dict):
        raise EvalFailure(f"{tool_name} failed")
    return result.structuredContent


async def _evaluate_session(
    session: Any,
    cases: Sequence[EvalCase],
    knowledge_root: Path,
    search_limit: int,
    ask_top_k: int,
) -> tuple[EvalRow, ...]:
    """在已初始化 session 中执行 index、逐题检索和 live 回答。"""
    indexed = await session.call_tool(
        "hy3_kb_index_documents",
        arguments={
            "collection": "evaluation",
            "path": os.fspath(knowledge_root.resolve()),
            "replace": True,
        },
    )
    _tool_payload(indexed, "index")

    rows = []
    for number, case in enumerate(cases, start=1):
        started = time.monotonic()
        searched = await session.call_tool(
            "hy3_kb_search",
            arguments={
                "collection": "evaluation",
                "query": case.question,
                "limit": search_limit,
            },
        )
        search_payload = _tool_payload(searched, "search")
        search_sources = tuple(
            str(item.get("source_path", ""))
            for item in search_payload.get("results", ())
            if isinstance(item, dict)
        )

        missing_search = _missing_suffixes(case.sources, search_sources)
        actual_answer: str | None = None
        citation_sources: tuple[str, ...] = ()
        if not missing_search:
            asked = await session.call_tool(
                "hy3_kb_ask",
                arguments={
                    "collection": "evaluation",
                    "question": case.question,
                    "top_k": ask_top_k,
                },
            )
            if not asked.isError and isinstance(asked.structuredContent, dict):
                ask_payload = asked.structuredContent
                raw_answer = ask_payload.get("answer")
                actual_answer = raw_answer if isinstance(raw_answer, str) else None
                citation_sources = tuple(
                    str(item.get("source_path", ""))
                    for item in ask_payload.get("citations", ())
                    if isinstance(item, dict)
                )

        rows.append(
            evaluate_row(
                number=number,
                question=case.question,
                expected_answer=case.answer,
                declared_sources=case.sources,
                search_sources=search_sources,
                actual_answer=actual_answer,
                citation_sources=citation_sources,
                duration_seconds=time.monotonic() - started,
            )
        )
    return tuple(rows)


def _parse_args(argv: Sequence[str] | None) -> Namespace:
    """解析 live 评测路径、server 命令与检索参数。"""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--knowledge-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--command", default="hy3-knowledge-mcp")
    parser.add_argument("--server-arg", action="append", default=[])
    parser.add_argument("--search-limit", type=int, default=12, choices=range(1, 21))
    parser.add_argument("--ask-top-k", type=int, default=12, choices=range(1, 13))
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    return parser.parse_args(argv)


def _installed_version() -> str:
    """读取已安装发行版版本; 缺失时使用包内版本。"""
    try:
        return version("hy3-knowledge-mcp")
    except PackageNotFoundError:
        from hy3_knowledge_mcp import __version__

        return __version__


def _git_commit() -> str:
    """读取当前 checkout commit; 不把 git 错误写入报告。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PACKAGE_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return "unavailable"
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and commit else "unavailable"


async def _run_live(
    options: Namespace,
    environ: Mapping[str, str],
    cases: Sequence[EvalCase],
) -> tuple[EvalMetadata, tuple[EvalRow, ...]]:
    """使用临时索引和已安装 stdio server 执行一次真实评测。"""
    knowledge_root = options.knowledge_root.resolve()
    with tempfile.TemporaryDirectory(prefix="hy3-eval-") as temp_dir:
        temp_root = Path(temp_dir)
        child_env = build_child_environment(environ, knowledge_root, temp_root / "storage")
        stderr_path = temp_root / "server.stderr.log"
        server = StdioServerParameters(
            command=options.command,
            args=options.server_arg,
            cwd=PACKAGE_ROOT,
            env=child_env,
            encoding="utf-8",
            encoding_error_handler="strict",
        )
        with stderr_path.open("w", encoding="utf-8") as errlog:
            with anyio.fail_after(options.timeout_seconds):
                async with stdio_client(server, errlog=errlog) as (read, write):
                    async with ClientSession(
                        read,
                        write,
                        read_timeout_seconds=timedelta(seconds=options.timeout_seconds),
                    ) as session:
                        await session.initialize()
                        rows = await _evaluate_session(
                            session,
                            cases,
                            knowledge_root,
                            options.search_limit,
                            options.ask_top_k,
                        )

    metadata = EvalMetadata(
        model=environ.get("HY3_MODEL", "hy3"),
        endpoint_profile=environ.get("HY3_ENDPOINT_PROFILE", "local"),
        reasoning_effort=environ.get("HY3_REASONING_EFFORT", "high"),
        package_version=_installed_version(),
        git_commit=_git_commit(),
        corpus_sha256=corpus_sha256(knowledge_root),
        endpoint_host=safe_endpoint_host(environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1")),
        timestamp_utc=datetime.now(timezone.utc),
        search_limit=options.search_limit,
        ask_top_k=options.ask_top_k,
    )
    return metadata, rows


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    """运行 live 评测; 仅在真实 session 完成后写报告。"""
    source_env = os.environ if environ is None else environ
    options = _parse_args(argv)
    try:
        _prepare_output(options.output)
    except EvalFailure:
        print("EVALUATION FAILED: report output is unavailable", file=sys.stderr)
        return 1
    if not source_env.get("HY3_API_KEY", "").strip():
        print("EVALUATION FAILED: HY3_API_KEY is required", file=sys.stderr)
        return 1
    if not options.evaluation.is_file() or not options.knowledge_root.is_dir():
        print("EVALUATION FAILED: evaluation input is unavailable", file=sys.stderr)
        return 1
    if options.timeout_seconds <= 0:
        print("EVALUATION FAILED: timeout must be positive", file=sys.stderr)
        return 1

    try:
        cases = parse_evaluation(options.evaluation)
        if len(cases) != 10:
            raise EvalFailure("evaluation must contain ten questions")
        metadata, rows = anyio.run(_run_live, options, source_env, cases)
    except BaseException:
        print("EVALUATION FAILED: live MCP run did not complete", file=sys.stderr)
        return 1

    try:
        _atomic_write_text(options.output, render_report(metadata, rows))
    except EvalFailure:
        print("EVALUATION FAILED: report write did not complete", file=sys.stderr)
        return 1
    passed = sum(row.passed for row in rows)
    print(f"EVALUATION COMPLETE: {passed}/{len(rows)}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
