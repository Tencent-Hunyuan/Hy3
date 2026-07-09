"""Tests for the verdict schema module: extract_json / parse_verdict / AuditVerdict."""

from __future__ import annotations

import pydantic
import pytest

from hy3_security_mcp.schemas import (
    AuditLevel,
    AuditVerdict,
    DiffReviewReport,
    FindingSeverity,
    SecretScanReport,
    SecretVerdict,
    SecurityCategory,
    SecurityFinding,
    VerdictParseError,
    VulnAdvisory,
    VulnIntelReport,
    extract_json,
    parse_review_report,
    parse_secret_report,
    parse_verdict,
    parse_vuln_report,
)

_CLEAN_VERDICT = (
    '{"level": "deny", "category": "destructive_fs", '
    '"rationale": "删除系统路径不可逆", "safer_alternative": null}'
)

_EXPECTED_DICT = {
    "level": "deny",
    "category": "destructive_fs",
    "rationale": "删除系统路径不可逆",
    "safer_alternative": None,
}


class TestExtractJson:
    def test_clean_json(self) -> None:
        assert extract_json(_CLEAN_VERDICT) == _EXPECTED_DICT

    def test_json_fenced_block(self) -> None:
        text = f"```json\n{_CLEAN_VERDICT}\n```"
        assert extract_json(text) == _EXPECTED_DICT

    def test_plain_fenced_block(self) -> None:
        text = f"```\n{_CLEAN_VERDICT}\n```"
        assert extract_json(text) == _EXPECTED_DICT

    def test_prefixed_prose_then_json(self) -> None:
        text = f"好的，以下是我的审计结论：\n{_CLEAN_VERDICT}"
        assert extract_json(text) == _EXPECTED_DICT

    def test_json_then_trailing_prose(self) -> None:
        text = f"{_CLEAN_VERDICT}\n以上就是本次审计的全部判断。"
        assert extract_json(text) == _EXPECTED_DICT

    def test_nested_braces_inside_string_values(self) -> None:
        text = (
            '审计结果：{"level": "deny", "category": null, '
            '"rationale": "命令 rm -rf {dir} 中的 {dir} 展开后指向根目录", '
            '"safer_alternative": null} 请谨慎。'
        )
        result = extract_json(text)
        assert result["rationale"] == "命令 rm -rf {dir} 中的 {dir} 展开后指向根目录"
        assert result["level"] == "deny"

    def test_no_json_raises_with_excerpt(self) -> None:
        text = "这条命令看起来没什么问题，放心执行即可。"
        with pytest.raises(VerdictParseError) as exc_info:
            extract_json(text)
        assert text in str(exc_info.value)

    def test_excerpt_is_truncated_to_200_chars(self) -> None:
        text = "x" * 500
        with pytest.raises(VerdictParseError) as exc_info:
            extract_json(text)
        message = str(exc_info.value)
        assert "x" * 200 in message
        assert "x" * 201 not in message

    def test_top_level_non_object_json_raises(self) -> None:
        with pytest.raises(VerdictParseError):
            extract_json('["deny", "allow"]')


class TestEnums:
    def test_audit_level_values(self) -> None:
        assert AuditLevel.ALLOW == "allow"
        assert AuditLevel.CONFIRM == "confirm"
        assert AuditLevel.DENY == "deny"

    def test_security_category_values(self) -> None:
        assert {c.value for c in SecurityCategory} == {
            "destructive_fs",
            "sensitive_file",
            "network_exfil",
            "persistence",
            "backdoor",
            "ssh_keys",
            "sudoers",
        }


class TestParseVerdict:
    def test_valid_full_verdict(self) -> None:
        verdict = parse_verdict(_CLEAN_VERDICT, source="llm")

        assert verdict == AuditVerdict(
            level=AuditLevel.DENY,
            category=SecurityCategory.DESTRUCTIVE_FS,
            rationale="删除系统路径不可逆",
            safer_alternative=None,
            source="llm",
        )

    def test_null_category_and_safer_alternative_string(self) -> None:
        text = (
            '{"level": "confirm", "category": null, '
            '"rationale": "范围过大", "safer_alternative": "rm -rf ./build"}'
        )
        verdict = parse_verdict(text, source="llm")

        assert verdict.category is None
        assert verdict.safer_alternative == "rm -rf ./build"

    def test_source_is_set_by_caller_not_llm(self) -> None:
        text = (
            '{"level": "allow", "category": null, "rationale": "只读操作", "source": "fast_path"}'
        )
        verdict = parse_verdict(text, source="llm")

        assert verdict.source == "llm"

    def test_bad_level_value_raises(self) -> None:
        text = '{"level": "maybe", "category": null, "rationale": "含糊"}'
        with pytest.raises(VerdictParseError) as exc_info:
            parse_verdict(text, source="llm")
        assert "maybe" in str(exc_info.value)

    def test_missing_rationale_raises(self) -> None:
        text = '{"level": "deny", "category": "backdoor"}'
        with pytest.raises(VerdictParseError) as exc_info:
            parse_verdict(text, source="llm")
        assert "rationale" in str(exc_info.value)

    def test_validation_error_does_not_leak_pydantic_exception(self) -> None:
        with pytest.raises(VerdictParseError):
            try:
                parse_verdict('{"level": "maybe", "rationale": 1}', source="llm")
            except pydantic.ValidationError:
                pytest.fail("raw pydantic.ValidationError escaped parse_verdict")


class TestFindingSeverity:
    def test_values_are_lowercase(self) -> None:
        assert {s.value for s in FindingSeverity} == {
            "critical",
            "high",
            "medium",
            "low",
            "info",
        }


class TestSecurityFinding:
    def test_optional_fields_default_to_none(self) -> None:
        finding = SecurityFinding(
            severity=FindingSeverity.HIGH,
            title="硬编码凭据",
            weakness="硬编码凭据",
            detail="新增代码中硬编码了 API 密钥",
        )

        assert finding.file is None
        assert finding.line is None
        assert finding.fix_suggestion is None


class TestParseReviewReport:
    _CLEAN_REPORT = (
        '{"findings": [{"severity": "critical", "title": "命令注入", '
        '"file": "app.py", "line": 12, "weakness": "命令注入", '
        '"detail": "os.system 直接执行未经校验的用户输入", '
        '"fix_suggestion": "改用参数化调用"}], "summary": "发现 1 处命令注入风险"}'
    )

    def test_valid_report_round_trips_severity_enum(self) -> None:
        report = parse_review_report(self._CLEAN_REPORT)

        assert isinstance(report, DiffReviewReport)
        assert len(report.findings) == 1
        assert report.findings[0].severity == FindingSeverity.CRITICAL
        assert report.findings[0].file == "app.py"
        assert report.findings[0].line == 12

    def test_empty_findings_list_is_valid(self) -> None:
        report = parse_review_report('{"findings": [], "summary": "未发现安全问题"}')

        assert report.findings == []
        assert report.summary == "未发现安全问题"

    def test_malformed_text_raises_verdict_parse_error(self) -> None:
        with pytest.raises(VerdictParseError):
            parse_review_report("not json at all")

    def test_invalid_severity_raises_verdict_parse_error(self) -> None:
        text = (
            '{"findings": [{"severity": "extreme", "title": "x", '
            '"weakness": "x", "detail": "x"}], "summary": "x"}'
        )
        with pytest.raises(VerdictParseError) as exc_info:
            parse_review_report(text)
        assert "extreme" in str(exc_info.value)


class TestSecretVerdict:
    def test_optional_remediation_defaults_to_none(self) -> None:
        verdict = SecretVerdict(
            line=3,
            kind="OPENAI_KEY",
            is_true_positive=True,
            severity=FindingSeverity.HIGH,
            rationale="疑似真实的 OpenAI API 密钥",
        )

        assert verdict.remediation is None


class TestParseSecretReport:
    _CLEAN_REPORT = (
        '{"secrets": [{"line": 3, "kind": "OPENAI_KEY", "is_true_positive": true, '
        '"severity": "high", "rationale": "疑似真实的 OpenAI API 密钥", '
        '"remediation": "立即轮换密钥并移入密管服务"}], "summary": "发现 1 处疑似真实密钥"}'
    )

    def test_valid_report_round_trips_severity_enum(self) -> None:
        report = parse_secret_report(self._CLEAN_REPORT)

        assert isinstance(report, SecretScanReport)
        assert len(report.secrets) == 1
        assert report.secrets[0].severity == FindingSeverity.HIGH
        assert report.secrets[0].line == 3
        assert report.secrets[0].kind == "OPENAI_KEY"
        assert report.secrets[0].is_true_positive is True

    def test_empty_secrets_list_is_valid(self) -> None:
        report = parse_secret_report('{"secrets": [], "summary": "未发现候选密钥"}')

        assert report.secrets == []
        assert report.summary == "未发现候选密钥"

    def test_malformed_text_raises_verdict_parse_error(self) -> None:
        with pytest.raises(VerdictParseError):
            parse_secret_report("not json at all")

    def test_invalid_severity_raises_verdict_parse_error(self) -> None:
        text = (
            '{"secrets": [{"line": 1, "kind": "high_entropy", "is_true_positive": false, '
            '"severity": "extreme", "rationale": "x"}], "summary": "x"}'
        )
        with pytest.raises(VerdictParseError) as exc_info:
            parse_secret_report(text)
        assert "extreme" in str(exc_info.value)

    def test_false_positive_with_remediation_none(self) -> None:
        text = (
            '{"secrets": [{"line": 5, "kind": "high_entropy", "is_true_positive": false, '
            '"severity": "info", "rationale": "这是 git commit SHA,非凭据", '
            '"remediation": null}], "summary": "候选均为误报"}'
        )

        report = parse_secret_report(text)

        assert report.secrets[0].is_true_positive is False
        assert report.secrets[0].remediation is None


class TestVulnAdvisory:
    def test_references_defaults_to_empty_list(self) -> None:
        advisory = VulnAdvisory(
            vuln_id="GHSA-xxxx-xxxx-xxxx",
            severity=FindingSeverity.HIGH,
            affected="requests < 2.31.0",
            exploitability="需要构造恶意重定向",
            remediation="升级至 2.31.0 及以上版本",
        )

        assert advisory.references == []


class TestParseVulnReport:
    _CLEAN_REPORT = (
        '{"advisories": [{"vuln_id": "GHSA-xxxx-xxxx-xxxx", "severity": "high", '
        '"affected": "requests < 2.31.0", "exploitability": "需要构造恶意重定向", '
        '"remediation": "升级至 2.31.0 及以上版本", '
        '"references": ["https://osv.dev/GHSA-xxxx-xxxx-xxxx"]}], '
        '"summary": "发现 1 处高危漏洞", "overall_priority": "high"}'
    )

    def test_valid_report_round_trips_severity_and_priority_enums(self) -> None:
        report = parse_vuln_report(self._CLEAN_REPORT)

        assert isinstance(report, VulnIntelReport)
        assert len(report.advisories) == 1
        assert report.advisories[0].severity == FindingSeverity.HIGH
        assert report.advisories[0].vuln_id == "GHSA-xxxx-xxxx-xxxx"
        assert report.advisories[0].references == ["https://osv.dev/GHSA-xxxx-xxxx-xxxx"]
        assert report.overall_priority == FindingSeverity.HIGH

    def test_empty_advisories_list_is_valid(self) -> None:
        report = parse_vuln_report(
            '{"advisories": [], "summary": "未发现已知漏洞", "overall_priority": "info"}'
        )

        assert report.advisories == []
        assert report.summary == "未发现已知漏洞"
        assert report.overall_priority == FindingSeverity.INFO

    def test_malformed_text_raises_verdict_parse_error(self) -> None:
        with pytest.raises(VerdictParseError):
            parse_vuln_report("not json at all")

    def test_invalid_severity_raises_verdict_parse_error(self) -> None:
        text = (
            '{"advisories": [{"vuln_id": "GHSA-xxxx", "severity": "extreme", '
            '"affected": "x", "exploitability": "x", "remediation": "x"}], '
            '"summary": "x", "overall_priority": "high"}'
        )
        with pytest.raises(VerdictParseError) as exc_info:
            parse_vuln_report(text)
        assert "extreme" in str(exc_info.value)
