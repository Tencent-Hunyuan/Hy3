import json
import re
from pathlib import Path, PureWindowsPath

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CLIENT_EXAMPLES = {
    "cline.json",
    "trae.mcp.json",
    "codebuddy.mcp.json",
    "workbuddy.mcp.json",
}
TOOL_NAMES = {
    "hy3_kb_index_documents",
    "hy3_kb_search",
    "hy3_kb_ask",
    "hy3_kb_summarize_source",
    "hy3_kb_list_sources",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_client_examples_are_valid_json_without_real_secrets() -> None:
    examples_dir = PACKAGE_ROOT / "examples" / "clients"
    paths = sorted(examples_dir.glob("*.json"))

    assert {path.name for path in paths} == CLIENT_EXAMPLES
    for path in paths:
        text = _read(path)
        data = json.loads(text)
        assert data["mcpServers"]["hy3-knowledge"]
        assert "sk-or-" + "v1-" not in text
        assert "zhan" + "w" not in text.casefold()


def test_client_examples_use_the_documented_shapes() -> None:
    examples_dir = PACKAGE_ROOT / "examples" / "clients"
    cline = json.loads(_read(examples_dir / "cline.json"))["mcpServers"]["hy3-knowledge"]
    trae = json.loads(_read(examples_dir / "trae.mcp.json"))["mcpServers"]["hy3-knowledge"]
    codebuddy = json.loads(_read(examples_dir / "codebuddy.mcp.json"))["mcpServers"][
        "hy3-knowledge"
    ]
    workbuddy = json.loads(_read(examples_dir / "workbuddy.mcp.json"))["mcpServers"][
        "hy3-knowledge"
    ]

    assert cline["transport"]["type"] == "stdio"
    assert cline["transport"]["command"] == "uvx"
    assert trae["command"] == "uvx"
    assert trae["cwd"] == "${workspaceFolder}"
    assert any("${workspaceFolder}" in argument for argument in trae["args"])
    assert codebuddy["type"] == "stdio"
    assert codebuddy["args"][1] == "${HY3_MCP_SOURCE}"
    assert codebuddy["env"]["HY3_API_KEY"] == "${HY3_API_KEY}"
    assert all(re.fullmatch(r"\$\{[A-Z0-9_]+\}", value) for value in codebuddy["env"].values())
    assert "HY3_API_KEY" not in workbuddy["env"]


def test_windows_client_placeholders_share_one_replaceable_repository_root() -> None:
    examples_dir = PACKAGE_ROOT / "examples" / "clients"
    cline = json.loads(_read(examples_dir / "cline.json"))["mcpServers"]["hy3-knowledge"]
    workbuddy = json.loads(_read(examples_dir / "workbuddy.mcp.json"))["mcpServers"][
        "hy3-knowledge"
    ]
    repository = PureWindowsPath(r"C:\path\to\Hy3")
    package = repository / "mcp_servers" / "knowledge_base"
    knowledge_root = package / "examples" / "knowledge_base"

    assert PureWindowsPath(cline["transport"]["cwd"]) == repository
    assert PureWindowsPath(cline["transport"]["args"][1]) == package
    assert PureWindowsPath(workbuddy["args"][1]) == package
    assert PureWindowsPath(workbuddy["env"]["HY3_KB_ROOTS"]) == knowledge_root


def test_relative_markdown_links_exist() -> None:
    pattern = re.compile(r"\[[^\]]+\]\((?!https?://)([^)#]+)")
    documents = [
        PACKAGE_ROOT / "README.md",
        PACKAGE_ROOT / "README_CN.md",
        PACKAGE_ROOT / "docs" / "clients" / "cline.md",
        PACKAGE_ROOT / "docs" / "clients" / "trae.md",
        PACKAGE_ROOT / "docs" / "clients" / "codebuddy-workbuddy.md",
    ]

    for document in documents:
        for target in pattern.findall(_read(document)):
            assert (document.parent / target).resolve().exists(), f"{document}: {target}"


def test_readmes_cover_issue_acceptance_terms() -> None:
    english = _read(PACKAGE_ROOT / "README.md")
    chinese = _read(PACKAGE_ROOT / "README_CN.md")
    required = {
        *TOOL_NAMES,
        "pip install .",
        "uvx --from . hy3-knowledge-mcp",
        "CodeBuddy",
        "WorkBuddy",
        "Cline",
        "TRAE",
        "HY3_KB_ROOTS",
        "HY3_KB_STORAGE_DIR",
        "HY3_KB_MAX_FILE_BYTES",
        "tencent/hy3:free",
        "2026-07-21",
        'collection="demo"',
        "2025-11-18",
        "FTS5",
        "OCR",
        "429",
    }

    for term in required:
        assert term in english
        assert term in chinese
    assert english.index('HY3_ENDPOINT_PROFILE = "local"') < english.index(
        'HY3_ENDPOINT_PROFILE = "openrouter"'
    )
    assert chinese.index('HY3_ENDPOINT_PROFILE = "local"') < chinese.index(
        'HY3_ENDPOINT_PROFILE = "openrouter"'
    )
    for text in (english, chinese):
        assert "docs/demos/cline.gif" in text
        assert "docs/demos/trae.gif" in text
        assert "docs/demos/README.md" in text


def test_readmes_document_tool_boundaries_and_annotations() -> None:
    for name in ("README.md", "README_CN.md"):
        text = _read(PACKAGE_ROOT / name)
        for marker in [
            "readOnlyHint",
            "destructiveHint",
            "idempotentHint",
            "openWorldHint",
            "index → list → search → ask",
            "python scripts/stdio_smoke.py",
            "python scripts/run_eval.py",
            "python -m build",
            "pytest",
        ]:
            assert marker in text, f"{name}: {marker}"


def test_readmes_document_local_to_remote_data_flow_and_structured_results() -> None:
    flow_nodes = [
        "local_files",
        "safe_parse_chunk",
        "sqlite_fts5",
        "offline_tools",
        "selected_evidence",
        "hy3_endpoint",
        "citation_validation",
        "remote_tools",
    ]
    result_fields = [
        "discovered_sources",
        "indexed_sources",
        "updated_sources",
        "unchanged_sources",
        "skipped_sources",
        "failed_sources",
        "chunk_count",
        "errors",
        "reason",
        "total",
        "count",
        "offset",
        "has_more",
        "next_offset",
        "results",
        "evidence_id",
        "page_number",
        "line_start",
        "line_end",
        "score",
        "snippet",
        "answer",
        "grounded",
        "insufficient_evidence",
        "citations",
        "warnings",
        "summary",
        "coverage",
        "used_evidence_ids",
        "sources",
        "source_format",
        "size_bytes",
        "page_count",
        "content_sha256_prefix",
        "indexed_at",
    ]

    for name in ("README.md", "README_CN.md"):
        text = _read(PACKAGE_ROOT / name)
        for marker in flow_nodes:
            assert marker in text, f"{name}: {marker}"
        for field in result_fields:
            assert f"`{field}`" in text, f"{name}: {field}"


def test_readme_end_to_end_demos_index_the_allowlisted_current_directory() -> None:
    expected_call = 'hy3_kb_index_documents(collection="demo", path=".", recursive=true)'

    for name in ("README.md", "README_CN.md"):
        text = _read(PACKAGE_ROOT / name)
        assert expected_call in text, name

    english = _read(PACKAGE_ROOT / "README.md")
    chinese = _read(PACKAGE_ROOT / "README_CN.md")
    assert "single configured allowed root" in english
    assert "multiple roots" in english
    assert "唯一配置的允许根目录" in chinese
    assert "多个根目录" in chinese
    assert "allowlisted corpus as the current directory" not in english
    assert "以白名单语料目录作为当前目录" not in chinese


def test_readmes_describe_measured_reasoning_without_generalizing() -> None:
    english = _read(PACKAGE_ROOT / "README.md")
    chinese = _read(PACKAGE_ROOT / "README_CN.md")

    assert "tracked 10/10" in english
    assert "more stable" not in english
    assert "已跟踪的 10/10" in chinese
    assert "更稳定" not in chinese
    assert "# Maps to local no_think; low/high pass through" in english
    assert "# The client supplies EMPTY internally" in english


def test_client_guides_record_verified_commands_and_limits() -> None:
    cline = _read(PACKAGE_ROOT / "docs" / "clients" / "cline.md")
    trae = _read(PACKAGE_ROOT / "docs" / "clients" / "trae.md")
    buddies = _read(PACKAGE_ROOT / "docs" / "clients" / "codebuddy-workbuddy.md")

    for term in [
        "3.0.39",
        "CLINE_MCP_SETTINGS_PATH",
        "cline mcp add hy3-knowledge --yes -- uvx",
        "cline config mcp --json",
        "--scope project",
        "inherits",
    ]:
        assert term in cline
    for term in [
        "TRAE SOLO CN 0.1.25",
        "VS Code 1.107.1",
        ".trae/mcp.json",
        "trae.mcp.enableWorkspaceMcp",
        "${workspaceFolder}",
        "Output → MCP Server Host",
    ]:
        assert term in trae
    for term in [
        "codebuddy mcp add --scope project",
        "codebuddy mcp list",
        "codebuddy mcp get hy3-knowledge",
        "CODEBUDDY_AVAILABLE=False",
        "$env:HY3_API_KEY",
        "$env:HY3_BASE_URL",
        "$env:HY3_MODEL",
        "$env:HY3_ENDPOINT_PROFILE",
        "$env:HY3_REASONING_EFFORT",
        "$env:HY3_KB_ROOTS",
        ".mcp.json",
        ".workbuddy/mcp.json",
        "Plugins → MCP Servers → Configure MCP",
    ]:
        assert term in buddies
    assert "${HY3_BASE_URL:-" not in buddies
    assert "<YOUR_HY3_API_KEY>" not in buddies
    assert not re.search(r"workbuddy\s+mcp\s+(?:add|list|get)", buddies, re.IGNORECASE)


def test_codebuddy_guide_explains_shell_environment_lifetime() -> None:
    buddies = _read(PACKAGE_ROOT / "docs" / "clients" / "codebuddy-workbuddy.md")

    for term in [
        "do not persist",
        "same PowerShell",
        "supported launch method",
        "--help",
        "product documentation",
        "all variables are defined",
    ]:
        assert term in buddies
