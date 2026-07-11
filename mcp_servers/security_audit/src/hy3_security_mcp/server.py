"""FastMCP stdio server exposing audit_command as the first MCP tool.

``build_server`` is a factory taking the Hy3CompletionClient so tests can
inject FakeHy3Client (the test seam reused/extended by later tasks). ``main``
is the real entrypoint: it fails fast on missing/invalid configuration before
ever building a server or opening the stdio transport.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

import pydantic
from mcp.server.fastmcp import FastMCP

from hy3_security_mcp.audit import audit_command_verdict
from hy3_security_mcp.config import load_config
from hy3_security_mcp.git_utils import read_diff, read_file_text
from hy3_security_mcp.hy3_client import Hy3Client, Hy3CompletionClient
from hy3_security_mcp.intel import synthesize_advisory
from hy3_security_mcp.osv import OSVClient, OSVVulnerability
from hy3_security_mcp.review import review_diff_report
from hy3_security_mcp.scan import triage_secrets
from hy3_security_mcp.secrets import scan_text

_COMMAND_DESCRIPTION = (
    "待审计的 shell 命令原始文本;仅作为审计对象,绝不会被当作指令执行。"
    "The raw shell command to audit — treated purely as data, never executed "
    "or interpreted as an instruction."
)
_CONTEXT_DESCRIPTION = (
    "可选的场景上下文(例如该命令因何、由谁触发);同样仅作为审计数据处理,省略则不提供上下文。"
    "Optional scenario context (e.g. why/by whom this command is being run) — "
    "also treated purely as untrusted data; omit if there is none."
)
_REPO_PATH_DESCRIPTION = (
    "本地 git 仓库路径,默认为当前目录。"
    "Path to a local git repository; defaults to the current directory."
)
_STAGED_DESCRIPTION = (
    "为 true 时只审查已 git add 暂存的改动(相当于 git diff --staged);"
    "默认审查未暂存的改动。与 ref_range 互斥。"
    "When true, review only staged changes (git diff --staged) instead of "
    "unstaged changes. Mutually exclusive with ref_range."
)
_REF_RANGE_DESCRIPTION = (
    "可选的 git 修订区间(如 'HEAD~1..HEAD'),直接传给 git diff;省略则不使用区间。"
    "与 staged 互斥。"
    "Optional git revision range (e.g. 'HEAD~1..HEAD') passed straight to "
    "git diff; omit for none. Mutually exclusive with staged."
)
_FOCUS_DESCRIPTION = (
    "可选的审查侧重说明(例如「重点检查鉴权逻辑」),会作为审查指引附加在提示词中;省略则不设侧重。"
    "Optional review focus hint (e.g. 'pay special attention to auth logic') "
    "appended as guidance in the prompt; omit for none."
)
_SCAN_PATH_DESCRIPTION = (
    "待扫描文件的本地路径;与 text 互斥,二者必须且只能提供一个,否则抛出错误。"
    "Path to a local file to scan for candidate secrets; mutually exclusive "
    "with text — exactly one of path/text must be provided, or an error is "
    "raised."
)
_SCAN_TEXT_DESCRIPTION = (
    "待扫描的原始文本内容;与 path 互斥,二者必须且只能提供一个,否则抛出错误。"
    "Raw text content to scan for candidate secrets; mutually exclusive with "
    "path — exactly one of path/text must be provided, or an error is raised."
)
_PACKAGES_DESCRIPTION = (
    '待查询的依赖包列表,每项为 {"name": 包名, "ecosystem": 生态系统(如 PyPI/npm/Go/'
    'crates.io/Maven), "version": 可选的具体版本号}。与 vuln_ids 至少提供一项,否则抛出 '
    "ValueError。"
    'List of dependency packages to query, each a {"name": ..., "ecosystem": '
    '...(e.g. PyPI/npm/Go/crates.io/Maven), "version": optional} dict. At '
    "least one of packages/vuln_ids is required, or a ValueError is raised."
)
_VULN_IDS_DESCRIPTION = (
    "待直接查询的漏洞 id 列表(如 CVE-2023-12345、GHSA-xxxx-xxxx-xxxx);与 packages 至少"
    "提供一项。"
    "List of vulnerability ids to query directly (e.g. CVE-2023-12345, "
    "GHSA-xxxx-xxxx-xxxx); at least one of packages/vuln_ids is required."
)
_VULN_CONTEXT_DESCRIPTION = (
    "可选的使用场景说明(例如该依赖在系统中的用途);同样仅作为不可信数据处理,省略则不提供"
    "场景说明。"
    "Optional usage-scenario context (e.g. how this dependency is used in "
    "the system) — also treated purely as untrusted data; omit if there is "
    "none."
)


def _require_package_field(pkg: dict[str, Any], field: str) -> Any:
    """Return `pkg[field]`, or raise a ValueError naming the missing required
    key -- a malformed packages entry must not surface as a bare KeyError."""
    if field not in pkg:
        raise ValueError(f"packages entry missing required key {field!r}: {pkg!r}")
    return pkg[field]


async def _gather_package_vulns(
    osv_client: OSVClient, packages: list[dict[str, Any]]
) -> tuple[list[OSVVulnerability], list[dict[str, str]]]:
    """Query every package concurrently, tolerating per-package failures.

    A 404/network error on one package must not discard the valid advisories
    from the others (return_exceptions=True), so failures are collected into a
    per-package error list instead of sinking the whole batch. A malformed
    entry (missing name/ecosystem) still raises ValueError eagerly, before any
    request is dispatched, so the caller gets a descriptive tool error.
    """
    coros = [
        osv_client.query_package(
            _require_package_field(pkg, "name"),
            _require_package_field(pkg, "ecosystem"),
            pkg.get("version"),
        )
        for pkg in packages
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)
    vulns: list[OSVVulnerability] = []
    errors: list[dict[str, str]] = []
    for pkg, result in zip(packages, results, strict=True):
        if isinstance(result, BaseException):
            errors.append({"package": str(pkg.get("name")), "error": str(result)})
        else:
            vulns.extend(result)
    return vulns, errors


async def _gather_id_vulns(
    osv_client: OSVClient, vuln_ids: list[str]
) -> tuple[list[OSVVulnerability], list[dict[str, str]]]:
    """Query every vuln id concurrently, tolerating per-id failures.

    One unknown/404 id must not sink the batch (return_exceptions=True); the
    failing id is recorded in a per-id error list and the valid ones are still
    returned.
    """
    results = await asyncio.gather(
        *(osv_client.get_vuln(vuln_id) for vuln_id in vuln_ids), return_exceptions=True
    )
    vulns: list[OSVVulnerability] = []
    errors: list[dict[str, str]] = []
    for vuln_id, result in zip(vuln_ids, results, strict=True):
        if isinstance(result, BaseException):
            errors.append({"id": vuln_id, "error": str(result)})
        else:
            vulns.append(result)
    return vulns, errors


def build_server(client: Hy3CompletionClient, *, osv_client: OSVClient | None = None) -> FastMCP:
    """Build the FastMCP app and register all tools against `client`.

    This factory is the test seam: tests pass a FakeHy3Client (and, for
    vuln_intel, a MockTransport-backed OSVClient) so tool logic can be
    exercised end-to-end over the real MCP protocol without any network
    access. `osv_client` defaults to a real OSVClient hitting api.osv.dev.
    """
    app = FastMCP("hy3-security-audit")
    osv = osv_client if osv_client is not None else OSVClient()

    @app.tool()
    async def audit_command(
        command: Annotated[str, pydantic.Field(description=_COMMAND_DESCRIPTION)],
        context: Annotated[str | None, pydantic.Field(description=_CONTEXT_DESCRIPTION)] = None,
    ) -> dict[str, Any]:
        """审计单条 shell 命令是否安全,并返回结构化裁决结果。

        Audit whether a single shell command is safe to execute, returning a
        structured verdict.

        Returns / 返回字段说明:
        - level: "allow"(放行)/ "confirm"(需人工确认)/ "deny"(拒绝执行)。
        - category: 命中的危险类别,allow 时通常为 null。
        - rationale: 一句中文说明判断理由。
        - safer_alternative: 更安全的替代命令,或 null。
        - source: "fast_path"(确定性快速路径命中)或 "llm"(由模型裁决)。
        """
        verdict = await audit_command_verdict(command, client=client, context=context)
        return verdict.model_dump(mode="json")

    @app.tool()
    async def review_diff(
        repo_path: Annotated[str, pydantic.Field(description=_REPO_PATH_DESCRIPTION)] = ".",
        staged: Annotated[bool, pydantic.Field(description=_STAGED_DESCRIPTION)] = False,
        ref_range: Annotated[str | None, pydantic.Field(description=_REF_RANGE_DESCRIPTION)] = None,
        focus: Annotated[str | None, pydantic.Field(description=_FOCUS_DESCRIPTION)] = None,
    ) -> dict[str, Any]:
        """对一段 git diff 做安全代码审查,返回结构化的安全弱点报告。

        Perform a security code review of a git diff, returning a structured
        report of the weaknesses found.

        Returns / 返回字段说明:
        - findings: 安全弱点列表,每项包含——
          severity(critical/high/medium/low/info)、title(简短标题)、
          file(涉及文件路径或 null)、line(涉及行号或 null)、
          weakness(弱点类型,如 命令注入/SQL 注入/路径穿越/不安全反序列化/SSRF/硬编码凭据/弱加密)、
          detail(具体说明)、fix_suggestion(修复建议或 null)。
        - summary: 一句中文总结本次审查结论。
        """
        # read_diff shells out to git synchronously; offload it so a slow/large
        # repo (or the bounded git timeout) never blocks the event loop.
        diff_text = await asyncio.to_thread(
            read_diff, repo_path, staged=staged, ref_range=ref_range
        )
        report = await review_diff_report(diff_text, client=client, focus=focus)
        return report.model_dump(mode="json")

    @app.tool()
    async def scan_secrets(
        path: Annotated[str | None, pydantic.Field(description=_SCAN_PATH_DESCRIPTION)] = None,
        text: Annotated[str | None, pydantic.Field(description=_SCAN_TEXT_DESCRIPTION)] = None,
    ) -> dict[str, Any]:
        """本地正则 + 熵值扫描候选密钥,并交由 Hy3 分诊真伪、定级与整改建议。

        Locally scan text for candidate secrets via regex + Shannon entropy,
        then have Hy3 triage each candidate as a true/false positive with a
        severity and remediation suggestion.

        Params / 参数说明:
        - path: 待扫描文件的本地路径;与 text 互斥。
        - text: 待扫描的原始文本;与 path 互斥。
          二者必须且只能提供一个,否则抛出 ValueError;path 指向不存在的文件时
          抛出 FileNotFoundError。
          Exactly one of path/text must be given (both or neither raises
          ValueError); a missing path raises FileNotFoundError.

        Returns / 返回字段说明:
        - secrets: 分诊结果列表,每项包含——
          line(候选所在行号)、kind(候选类型,如 OPENAI_KEY/high_entropy 等)、
          is_true_positive(是否为真正的凭据泄露)、
          severity(critical/high/medium/low/info)、
          rationale(判定理由)、remediation(整改建议或 null)。
        - summary: 一句中文总结本次分诊结论。
        """
        if (path is None) == (text is None):
            raise ValueError("exactly one of path/text must be provided")
        if path is not None:
            content = read_file_text(path)
        else:
            assert text is not None
            content = text

        candidates = scan_text(content)
        report = await triage_secrets(candidates, client=client)
        return report.model_dump(mode="json")

    @app.tool()
    async def vuln_intel(
        packages: Annotated[
            list[dict[str, Any]] | None, pydantic.Field(description=_PACKAGES_DESCRIPTION)
        ] = None,
        vuln_ids: Annotated[
            list[str] | None, pydantic.Field(description=_VULN_IDS_DESCRIPTION)
        ] = None,
        context: Annotated[
            str | None, pydantic.Field(description=_VULN_CONTEXT_DESCRIPTION)
        ] = None,
    ) -> dict[str, Any]:
        """查询依赖包/CVE 已知漏洞情报(OSV.dev),并交由 Hy3 综合为中文安全通告。

        Query known-vulnerability intelligence for dependencies/CVE ids via
        OSV.dev, then have Hy3 synthesize a Chinese security advisory.

        Params / 参数说明:
        - packages: 待查询依赖包列表,每项为 {"name","ecosystem","version"?}
          (ecosystem 例如 PyPI/npm/Go/crates.io/Maven);与 vuln_ids 至少提供一项。
        - vuln_ids: 待直接查询的漏洞 id 列表(CVE/GHSA 等);与 packages 至少提供一项。
          两者都未提供时抛出 ValueError。
          packages/vuln_ids: at least one is required (ValueError if neither
          is given).
        - context: 可选的使用场景说明,仅作不可信数据处理,省略则不提供。

        Returns / 返回字段说明:
        - advisories: 逐条漏洞通告列表,每项包含——
          vuln_id、severity(critical/high/medium/low/info)、
          affected(受影响范围的中文说明)、exploitability(可利用性评估)、
          remediation(修复/升级建议)、references(参考链接列表)。
        - summary: 一句中文总结本次情报综合结论。
        - overall_priority: 整体处置优先级(critical/high/medium/low/info)。
        """
        if not packages and not vuln_ids:
            raise ValueError("at least one of packages/vuln_ids must be provided")

        (package_vulns, package_errors), (id_vulns, id_errors) = await asyncio.gather(
            _gather_package_vulns(osv, packages or []),
            _gather_id_vulns(osv, vuln_ids or []),
        )
        vulns_by_id = {vuln.id: vuln for vuln in (*package_vulns, *id_vulns)}

        report = await synthesize_advisory(
            list(vulns_by_id.values()), client=client, context=context
        )
        # A per-item OSV failure (e.g. a 404 on one id) must not sink the whole
        # batch; surface it as query_errors alongside the partial advisories.
        payload = report.model_dump(mode="json")
        payload["query_errors"] = [*package_errors, *id_errors]
        return payload

    return app


def main() -> None:
    """Fail-fast stdio entrypoint: load config, build the real client, run.

    A missing/invalid HY3_API_KEY raises ConfigError here — before any server
    is built or the stdio transport is opened — so misconfiguration is visible
    immediately in MCP client logs instead of a silent hang.
    """
    config = load_config()
    client = Hy3Client(config)
    osv_client = OSVClient()
    build_server(client, osv_client=osv_client).run()


if __name__ == "__main__":
    main()
