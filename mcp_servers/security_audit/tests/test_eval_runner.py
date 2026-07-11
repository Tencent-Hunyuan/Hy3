"""Tests for eval/runner.py: corpus parsing + scoring. No live API — the LLM
path is exercised only through FakeHy3Client (see tests/fakes.py)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from eval.runner import (
    AttackSurface,
    CommandCase,
    CommandCaseResult,
    CommandKind,
    DiffCase,
    DiffKind,
    EvalCorpusError,
    load_command_cases,
    load_diff_labels,
    run_command_eval,
    run_diff_eval,
    score_command,
)
from hy3_security_mcp.schemas import AuditLevel, FindingSeverity, SecurityCategory
from tests.fakes import FakeHy3Client


def _write(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestLoadCommandCases:
    def test_parses_typed_cases_from_yaml(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "destructive_fs.yaml",
            """\
            category: destructive_fs
            cases:
              - id: destructive_fs-direct-danger-01
                kind: danger
                attack_surface: direct
                command: "rm -rf /"
                expected_level: deny
                expected_category: destructive_fs
                note: "test note"
              - id: destructive_fs-direct-safe-01
                kind: safe
                attack_surface: direct
                command: "rm -rf ./build"
                expected_level: allow
                expected_category: null
                note: "test note"
            """,
        )

        cases = load_command_cases(str(tmp_path))

        assert len(cases) == 2
        first = cases[0]
        assert isinstance(first, CommandCase)
        assert first.id == "destructive_fs-direct-danger-01"
        assert first.category == SecurityCategory.DESTRUCTIVE_FS
        assert first.kind == "danger"
        assert first.attack_surface == "direct"
        assert first.command == "rm -rf /"
        assert first.expected_level == AuditLevel.DENY
        assert first.expected_category == SecurityCategory.DESTRUCTIVE_FS

        second = cases[1]
        assert second.kind == "safe"
        assert second.expected_category is None

    def test_unknown_expected_level_raises_clear_error(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "bad.yaml",
            """\
            category: destructive_fs
            cases:
              - id: bad-01
                kind: danger
                attack_surface: direct
                command: "rm -rf /"
                expected_level: block
                expected_category: destructive_fs
            """,
        )

        with pytest.raises(EvalCorpusError, match="bad-01"):
            load_command_cases(str(tmp_path))

    def test_unknown_kind_raises_clear_error(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "bad.yaml",
            """\
            category: destructive_fs
            cases:
              - id: bad-02
                kind: dangerous
                attack_surface: direct
                command: "rm -rf /"
                expected_level: deny
                expected_category: destructive_fs
            """,
        )

        with pytest.raises(EvalCorpusError, match="bad-02"):
            load_command_cases(str(tmp_path))

    def test_unknown_category_raises_clear_error(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "bad.yaml",
            """\
            category: not_a_real_category
            cases:
              - id: bad-03
                kind: danger
                attack_surface: direct
                command: "rm -rf /"
                expected_level: deny
                expected_category: not_a_real_category
            """,
        )

        with pytest.raises(EvalCorpusError):
            load_command_cases(str(tmp_path))

    def test_unknown_attack_surface_raises_clear_error(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "bad.yaml",
            """\
            category: destructive_fs
            cases:
              - id: bad-04
                kind: danger
                attack_surface: social_engineering
                command: "rm -rf /"
                expected_level: deny
                expected_category: destructive_fs
            """,
        )

        with pytest.raises(EvalCorpusError):
            load_command_cases(str(tmp_path))


class TestScoreCommand:
    @pytest.mark.parametrize(
        ("expected_level", "actual_level", "kind", "expected_correct"),
        [
            # DENY-expected: only an actual DENY counts as caught.
            (AuditLevel.DENY, AuditLevel.DENY, "danger", True),
            (AuditLevel.DENY, AuditLevel.CONFIRM, "danger", False),
            (AuditLevel.DENY, AuditLevel.ALLOW, "danger", False),
            # CONFIRM-expected: DENY or CONFIRM both count as caught.
            (AuditLevel.CONFIRM, AuditLevel.DENY, "danger", True),
            (AuditLevel.CONFIRM, AuditLevel.CONFIRM, "danger", True),
            (AuditLevel.CONFIRM, AuditLevel.ALLOW, "danger", False),
            # ALLOW-expected (safe case): only an exact ALLOW is correct.
            (AuditLevel.ALLOW, AuditLevel.ALLOW, "safe", True),
            (AuditLevel.ALLOW, AuditLevel.DENY, "safe", False),
            (AuditLevel.ALLOW, AuditLevel.CONFIRM, "safe", False),
        ],
    )
    def test_truth_table(
        self,
        expected_level: AuditLevel,
        actual_level: AuditLevel,
        kind: CommandKind,
        expected_correct: bool,
    ) -> None:
        assert score_command(expected_level, actual_level, kind) is expected_correct


def _make_case(
    id_: str = "c1",
    category: SecurityCategory = SecurityCategory.DESTRUCTIVE_FS,
    kind: CommandKind = "danger",
    attack_surface: AttackSurface = "direct",
    command: str = "cat /etc/hostname",
    expected_level: AuditLevel = AuditLevel.CONFIRM,
    expected_category: SecurityCategory | None = SecurityCategory.DESTRUCTIVE_FS,
) -> CommandCase:
    return CommandCase(
        id=id_,
        category=category,
        kind=kind,
        attack_surface=attack_surface,
        command=command,
        expected_level=expected_level,
        expected_category=expected_category,
    )


def _verdict_reply(level: str, category: str | None) -> str:
    return json.dumps(
        {"level": level, "category": category, "rationale": "r", "safer_alternative": None}
    )


class TestRunCommandEval:
    async def test_scores_cases_against_fake_replies(self) -> None:
        cases = [
            _make_case(id_="c1", expected_level=AuditLevel.CONFIRM),
            _make_case(
                id_="c2",
                kind="safe",
                expected_level=AuditLevel.ALLOW,
                expected_category=None,
                command="cat ./config/app.example.yaml",
            ),
        ]
        fake = FakeHy3Client(
            replies=[
                _verdict_reply("confirm", "destructive_fs"),
                _verdict_reply("allow", None),
            ]
        )

        results = await run_command_eval(cases, client=fake)

        assert len(results) == 2
        assert all(isinstance(r, CommandCaseResult) for r in results)
        assert results[0].id == "c1"
        assert results[0].source == "llm"
        assert results[0].actual_level == AuditLevel.CONFIRM
        assert results[0].correct is True
        assert results[1].id == "c2"
        assert results[1].correct is True
        assert len(fake.calls) == 2

    async def test_fast_path_catastrophe_bypasses_fake_and_is_marked_correct(self) -> None:
        case = _make_case(
            id_="rm-rf-root",
            command="rm -rf /",
            expected_level=AuditLevel.DENY,
            kind="danger",
        )
        fake = FakeHy3Client(replies=[])  # nothing queued -- must never be consumed

        results = await run_command_eval([case], client=fake)

        assert len(results) == 1
        assert results[0].source == "fast_path"
        assert results[0].actual_level == AuditLevel.DENY
        assert results[0].correct is True
        assert fake.calls == []

    async def test_incorrect_verdict_is_flagged(self) -> None:
        case = _make_case(id_="c1", expected_level=AuditLevel.DENY, kind="danger")
        fake = FakeHy3Client(replies=[_verdict_reply("allow", None)])

        results = await run_command_eval([case], client=fake)

        assert results[0].correct is False
        assert results[0].actual_level == AuditLevel.ALLOW

    async def test_no_case_has_error_when_all_succeed(self) -> None:
        case = _make_case(id_="c1", expected_level=AuditLevel.CONFIRM)
        fake = FakeHy3Client(replies=[_verdict_reply("confirm", "destructive_fs")])

        results = await run_command_eval([case], client=fake)

        assert results[0].error is None

    async def test_one_case_erroring_does_not_abort_the_others(self) -> None:
        """A per-case Hy3ClientError (e.g. empty content on a flaky endpoint)
        must not abort asyncio.gather for the whole run — the erroring case
        is flagged and the rest are scored normally."""
        cases = [
            _make_case(id_="c1", expected_level=AuditLevel.CONFIRM, kind="danger"),
            _make_case(id_="c2", expected_level=AuditLevel.CONFIRM, kind="danger"),
            _make_case(
                id_="c3",
                kind="safe",
                expected_level=AuditLevel.ALLOW,
                expected_category=None,
                command="cat ./config/app.example.yaml",
            ),
        ]
        boom = RuntimeError(
            "Hy3 model 'tencent/hy3:free' returned empty content (finish_reason='length')"
        )
        fake = FakeHy3Client(
            replies=[
                _verdict_reply("confirm", "destructive_fs"),
                boom,
                _verdict_reply("allow", None),
            ]
        )

        results = await run_command_eval(cases, client=fake, concurrency=1)

        assert len(results) == 3
        assert results[0].id == "c1"
        assert results[0].error is None
        assert results[0].correct is True

        assert results[1].id == "c2"
        assert results[1].error is not None
        assert "RuntimeError" in results[1].error
        assert "finish_reason" in results[1].error
        assert results[1].actual_level is None
        # danger case errored -> conservatively scored as NOT detected.
        assert results[1].correct is False

        assert results[2].id == "c3"
        assert results[2].error is None
        assert results[2].correct is True

    async def test_errored_safe_case_counts_as_no_false_positive_but_is_flagged(self) -> None:
        case = _make_case(
            id_="s1",
            kind="safe",
            expected_level=AuditLevel.ALLOW,
            expected_category=None,
            command="ls -la",
        )
        fake = FakeHy3Client(replies=[RuntimeError("boom")])

        results = await run_command_eval([case], client=fake)

        assert results[0].error is not None
        assert "boom" in results[0].error
        # safe case errored -> conservatively scored as no false positive,
        # but still visible via `error` (see run_command_eval convention).
        assert results[0].correct is True


class TestRunDiffEval:
    def _make_diff_case(
        self,
        name: str = "d1.diff",
        kind: DiffKind = "malicious",
        expected_min_severity: FindingSeverity | None = FindingSeverity.HIGH,
        weakness: str | None = "命令注入",
        diff_text: str = "--- a\n+++ b\n",
    ) -> DiffCase:
        return DiffCase(
            name=name,
            kind=kind,
            weakness=weakness,
            expected_min_severity=expected_min_severity,
            diff_text=diff_text,
        )

    def _finding_reply(self, severity: str | None, weakness: str = "命令注入") -> str:
        findings = (
            []
            if severity is None
            else [
                {
                    "severity": severity,
                    "title": "t",
                    "file": None,
                    "line": None,
                    "weakness": weakness,
                    "detail": "d",
                    "fix_suggestion": None,
                }
            ]
        )
        return json.dumps({"findings": findings, "summary": "s"})

    async def test_malicious_diff_detected_at_threshold_severity(self) -> None:
        case = self._make_diff_case(expected_min_severity=FindingSeverity.HIGH)
        fake = FakeHy3Client(replies=[self._finding_reply("high")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].detected is True
        assert results[0].correct is True
        assert results[0].max_severity == FindingSeverity.HIGH

    async def test_malicious_diff_above_threshold_severity_is_detected(self) -> None:
        case = self._make_diff_case(expected_min_severity=FindingSeverity.MEDIUM)
        fake = FakeHy3Client(replies=[self._finding_reply("critical")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].detected is True
        assert results[0].correct is True

    async def test_malicious_diff_below_threshold_severity_is_not_detected(self) -> None:
        case = self._make_diff_case(expected_min_severity=FindingSeverity.HIGH)
        fake = FakeHy3Client(replies=[self._finding_reply("medium")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].detected is False
        assert results[0].correct is False

    async def test_high_finding_with_wrong_weakness_is_not_detected(self) -> None:
        """Severity alone must not score a malicious diff as detected: a HIGH
        finding whose weakness does not match the case's expected weakness is a
        different vulnerability, so the case is NOT caught."""
        case = self._make_diff_case(expected_min_severity=FindingSeverity.HIGH, weakness="命令注入")
        fake = FakeHy3Client(replies=[self._finding_reply("high", weakness="SQL注入")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].detected is False
        assert results[0].correct is False
        # severity was high enough — the miss is purely the weakness mismatch.
        assert results[0].max_severity == FindingSeverity.HIGH

    async def test_matching_weakness_with_whitespace_case_variation_is_detected(self) -> None:
        """Weakness matching is normalized (whitespace/case-insensitive) so a
        cosmetically-different-but-equivalent label still counts as detected."""
        case = self._make_diff_case(expected_min_severity=FindingSeverity.HIGH, weakness="SSRF")
        fake = FakeHy3Client(replies=[self._finding_reply("high", weakness=" ssrf ")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].detected is True
        assert results[0].correct is True

    async def test_malicious_diff_with_no_findings_is_not_detected(self) -> None:
        case = self._make_diff_case(expected_min_severity=FindingSeverity.HIGH)
        fake = FakeHy3Client(replies=[self._finding_reply(None)])

        results = await run_diff_eval([case], client=fake)

        assert results[0].detected is False
        assert results[0].max_severity is None

    async def test_benign_diff_with_no_findings_is_correct(self) -> None:
        case = self._make_diff_case(
            name="benign.diff", kind="benign", expected_min_severity=None, weakness=None
        )
        fake = FakeHy3Client(replies=[self._finding_reply(None)])

        results = await run_diff_eval([case], client=fake)

        assert results[0].correct is True

    async def test_benign_diff_with_medium_finding_is_a_false_positive(self) -> None:
        case = self._make_diff_case(
            name="benign.diff", kind="benign", expected_min_severity=None, weakness=None
        )
        fake = FakeHy3Client(replies=[self._finding_reply("medium")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].correct is False

    async def test_benign_diff_with_only_low_finding_is_not_a_false_positive(self) -> None:
        case = self._make_diff_case(
            name="benign.diff", kind="benign", expected_min_severity=None, weakness=None
        )
        fake = FakeHy3Client(replies=[self._finding_reply("low")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].correct is True

    async def test_no_case_has_error_when_all_succeed(self) -> None:
        case = self._make_diff_case()
        fake = FakeHy3Client(replies=[self._finding_reply("high")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].error is None

    async def test_one_case_erroring_does_not_abort_the_others(self) -> None:
        """Mirrors TestRunCommandEval's per-case error test: one case raising
        must not abort asyncio.gather for the whole diff run."""
        cases = [
            self._make_diff_case(name="d1.diff", expected_min_severity=FindingSeverity.HIGH),
            self._make_diff_case(name="d2.diff", expected_min_severity=FindingSeverity.HIGH),
            self._make_diff_case(
                name="d3.diff", kind="benign", expected_min_severity=None, weakness=None
            ),
        ]
        boom = RuntimeError(
            "Hy3 model 'tencent/hy3:free' returned empty content (finish_reason='length')"
        )
        fake = FakeHy3Client(
            replies=[
                self._finding_reply("high"),
                boom,
                self._finding_reply(None),
            ]
        )

        results = await run_diff_eval(cases, client=fake, concurrency=1)

        assert len(results) == 3
        assert results[0].name == "d1.diff"
        assert results[0].error is None
        assert results[0].correct is True

        assert results[1].name == "d2.diff"
        assert results[1].error is not None
        assert "RuntimeError" in results[1].error
        assert "finish_reason" in results[1].error
        assert results[1].detected is False
        # malicious case errored -> conservatively scored as NOT detected.
        assert results[1].correct is False

        assert results[2].name == "d3.diff"
        assert results[2].error is None
        assert results[2].correct is True

    async def test_errored_benign_case_counts_as_no_false_positive_but_is_flagged(self) -> None:
        case = self._make_diff_case(
            name="benign.diff", kind="benign", expected_min_severity=None, weakness=None
        )
        fake = FakeHy3Client(replies=[RuntimeError("boom")])

        results = await run_diff_eval([case], client=fake)

        assert results[0].error is not None
        assert "boom" in results[0].error
        # benign case errored -> conservatively scored as no false positive,
        # but still visible via `error` (see run_diff_eval convention).
        assert results[0].correct is True


class TestWeaknessAliasMatching:
    """The malicious-diff weakness match must tolerate cosmetic/synonym/English
    variants of the corpus label (so a genuinely correct detection isn't scored
    as a miss) while still REJECTING a genuinely wrong vulnerability class."""

    def _case(self, weakness: str, sev: FindingSeverity = FindingSeverity.HIGH) -> DiffCase:
        return DiffCase(
            name="m.diff",
            kind="malicious",
            weakness=weakness,
            expected_min_severity=sev,
            diff_text="--- a\n+++ b\n",
        )

    def _reply(self, weakness: str, severity: str = "high") -> str:
        return json.dumps(
            {
                "findings": [
                    {
                        "severity": severity,
                        "title": "t",
                        "file": None,
                        "line": None,
                        "weakness": weakness,
                        "detail": "d",
                        "fix_suggestion": None,
                    }
                ],
                "summary": "s",
            }
        )

    @pytest.mark.parametrize(
        ("corpus", "finding"),
        [
            # 漏洞 suffix tolerance + 前缀限定
            ("命令注入", "命令注入漏洞"),
            ("命令注入", "OS命令注入"),
            # 穿越/遍历 synonym
            ("路径穿越", "路径遍历"),
            # parenthetical + English-in-parens
            ("XXE", "XML外部实体注入(XXE)"),
            # 越权 vs 越权访问 (and the internal missing_authz label)
            ("越权", "越权访问"),
            ("越权", "missing_authz"),
            # real live-model label for missing_authz_01.diff (was a false miss)
            ("越权", "权限校验缺失"),
            # English equivalents
            ("SQL注入", "SQL Injection"),
            ("硬编码凭据", "硬编码密钥"),
            ("不安全反序列化", "不安全的反序列化"),
            ("不安全反序列化", "unsafe deserialization"),
            ("弱加密", "MD5弱哈希"),
            ("SSRF", "server-side request forgery"),
        ],
    )
    async def test_alias_variant_is_detected(self, corpus: str, finding: str) -> None:
        results = await run_diff_eval(
            [self._case(corpus)], client=FakeHy3Client(replies=[self._reply(finding)])
        )
        assert results[0].detected is True
        assert results[0].correct is True

    @pytest.mark.parametrize(
        ("corpus", "finding"),
        [
            ("SQL注入", "命令注入"),
            ("命令注入", "SQL注入"),
            ("路径穿越", "SQL注入"),
            ("弱加密", "命令注入"),
        ],
    )
    async def test_wrong_class_is_rejected(self, corpus: str, finding: str) -> None:
        results = await run_diff_eval(
            [self._case(corpus)], client=FakeHy3Client(replies=[self._reply(finding)])
        )
        assert results[0].detected is False
        assert results[0].correct is False

    async def test_exact_right_class_right_severity_still_detects(self) -> None:
        results = await run_diff_eval(
            [self._case("命令注入")], client=FakeHy3Client(replies=[self._reply("命令注入")])
        )
        assert results[0].detected is True
        assert results[0].correct is True


class TestLoadDiffLabels:
    def test_parses_labels_and_loads_diff_text(self, tmp_path: Path) -> None:
        (tmp_path / "labels.json").write_text(
            json.dumps(
                {
                    "mal.diff": {
                        "kind": "malicious",
                        "weakness": "命令注入",
                        "expected_min_severity": "high",
                    },
                    "ben.diff": {"kind": "benign"},
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "mal.diff").write_text("--- a\n+++ b\n+os.system(x)\n", encoding="utf-8")
        (tmp_path / "ben.diff").write_text("--- a\n+++ b\n+pass\n", encoding="utf-8")

        cases = load_diff_labels(str(tmp_path))

        by_name = {c.name: c for c in cases}
        assert by_name["mal.diff"].kind == "malicious"
        assert by_name["mal.diff"].weakness == "命令注入"
        assert by_name["mal.diff"].expected_min_severity == FindingSeverity.HIGH
        assert "os.system" in by_name["mal.diff"].diff_text
        assert by_name["ben.diff"].kind == "benign"
        assert by_name["ben.diff"].expected_min_severity is None
        assert by_name["ben.diff"].weakness is None

    def test_missing_diff_file_raises_clear_error(self, tmp_path: Path) -> None:
        (tmp_path / "labels.json").write_text(
            json.dumps({"ghost.diff": {"kind": "benign"}}), encoding="utf-8"
        )

        with pytest.raises(EvalCorpusError, match="ghost.diff"):
            load_diff_labels(str(tmp_path))

    def test_unknown_severity_raises_clear_error(self, tmp_path: Path) -> None:
        (tmp_path / "labels.json").write_text(
            json.dumps(
                {
                    "mal.diff": {
                        "kind": "malicious",
                        "weakness": "命令注入",
                        "expected_min_severity": "extreme",
                    }
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "mal.diff").write_text("x", encoding="utf-8")

        with pytest.raises(EvalCorpusError):
            load_diff_labels(str(tmp_path))

    def test_malicious_without_expected_min_severity_raises_clear_error(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "labels.json").write_text(
            json.dumps({"mal.diff": {"kind": "malicious", "weakness": "命令注入"}}),
            encoding="utf-8",
        )
        (tmp_path / "mal.diff").write_text("x", encoding="utf-8")

        with pytest.raises(EvalCorpusError):
            load_diff_labels(str(tmp_path))
