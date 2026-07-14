"""分析流水线。

执行顺序固定为：
提取 -> 编号 -> 规则提取 -> 引用核验 -> 情景生成 -> 歧义分析 -> 引用核验 -> 聚合。

``judge_scenario`` 单独对某一题调用 Hy3 裁决并本地核验引用、计算得分。
业务层不依赖 Streamlit，可独立测试。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from ..config import Settings
from ..exceptions import EmptyDocumentError, FileTooLargeError
from ..ingestion.extractors import extract_text
from ..ingestion.source_indexer import SourceIndexer
from ..llm.hy3_client import Hy3ClientBase
from ..llm.prompts import (
    SYSTEM_PROMPT,
    build_ambiguity_prompt,
    build_judgment_prompt,
    build_rule_extraction_prompt,
    build_scenario_prompt,
)
from ..models import (
    AmbiguityReport,
    AnalysisBundle,
    Judgment,
    QuizAttempt,
    RuleExtractionResult,
    Scenario,
    ScenarioSet,
    SourceBlock,
    Verdict,
)
from .citation_verifier import CitationVerifier


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisService:
    def __init__(self, client: Hy3ClientBase, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        self.indexer = SourceIndexer()
        self.verifier = CitationVerifier()

    # ------------------------------------------------------------------ #
    # 公共入口
    # ------------------------------------------------------------------ #
    def analyze_document(
        self,
        file_name: str,
        file_bytes: bytes,
        progress: Callable[[str], None] | None = None,
    ) -> AnalysisBundle:
        def emit(message: str) -> None:
            if progress is not None:
                progress(message)

        # 0. 大小校验（提取前）
        if len(file_bytes) > self.settings.max_file_bytes:
            raise FileTooLargeError(
                user_message=(
                    f"文件大小超过上限（{self.settings.max_file_mb} MB），请压缩或拆分后重试。"
                )
            )

        # 1. 提取
        doc = extract_text(file_name, file_bytes)
        emit("① 提取文本与生成来源编号…")

        # 2. 字符数校验（提取后，不静默截断）
        if len(doc.full_text) > self.settings.max_chars:
            raise FileTooLargeError(
                user_message=(
                    f"文档提取后字符数（{len(doc.full_text)}）超过上限"
                    f"（{self.settings.max_chars}），请上传更短或分段后的文档。"
                )
            )

        # 3. 来源编号
        indexed = self.indexer.index(doc.pages)
        sources = indexed.blocks
        by_id = indexed.by_id
        if not sources:
            raise EmptyDocumentError(user_message="文档未产生任何可引用的文本块，请检查文件内容。")

        emit("② 生成规则提取并核验引用…")
        emit("②-1 正在请求模型提取规则…")

        # 4. 规则提取
        rule_result = self.client.generate_validated(
            SYSTEM_PROMPT,
            build_rule_extraction_prompt(indexed.indexed_text),
            RuleExtractionResult,
            reasoning_effort="low",
        )
        emit("②-2 规则已返回，正在核验引用…")
        rule_result, rule_id_map = self._renumber_rules(rule_result)

        # 5. 规则引用核验
        rule_result = self._verify_rule_citations(rule_result, by_id)

        emit("③ 正在生成情景并重编号…")

        # 6. 情景生成（只发送规则 JSON，不重复发送完整文档）
        rules_json = rule_result.model_dump_json()
        scenario_set = self.client.generate_validated(
            SYSTEM_PROMPT, build_scenario_prompt(rules_json), ScenarioSet, reasoning_effort="low"
        )
        scenario_set = self._renumber_scenarios(scenario_set, rule_id_map)

        emit("④ 正在生成歧义报告并核验引用…")

        # 7. 歧义分析（规则 JSON + 完整编号文档）
        ambiguity = self.client.generate_validated(
            SYSTEM_PROMPT,
            build_ambiguity_prompt(rules_json, indexed.indexed_text),
            AmbiguityReport,
            reasoning_effort="low",
        )
        ambiguity = self._renumber_issues(ambiguity)
        ambiguity = self._verify_ambiguity_citations(ambiguity, by_id)

        # 8. 聚合
        return AnalysisBundle(
            file_name=file_name,
            file_sha256=doc.file_sha256,
            analyzed_at=_utcnow(),
            model_name=self.settings.hy3_model,
            sources=sources,
            rule_result=rule_result,
            scenario_set=scenario_set,
            ambiguity_report=ambiguity,
            attempts=[],
        )

    def judge_scenario(
        self, bundle: AnalysisBundle, scenario_id: str, user_verdict: Verdict
    ) -> QuizAttempt:
        scenario = self._find_scenario(bundle, scenario_id)
        related_rules = self._resolve_rules(bundle, scenario.related_rule_ids)
        by_id = {s.source_id: s for s in bundle.sources}

        related_sources = self._related_sources_text(related_rules, by_id)
        related_rules_json = _rules_to_json(related_rules)

        raw_user = user_verdict.value if isinstance(user_verdict, Verdict) else str(user_verdict)
        user_prompt = build_judgment_prompt(
            scenario.model_dump_json(),
            related_rules_json,
            related_sources,
            raw_user,
        )

        judgment = self.client.generate_validated(
            SYSTEM_PROMPT, user_prompt, Judgment, reasoning_effort="high"
        )
        # 核验裁决引用
        judgment = judgment.model_copy(
            update={"citations": self.verifier.verify(judgment.citations, by_id)}
        )

        is_correct = judgment.verdict == user_verdict
        attempt = QuizAttempt(
            scenario_id=scenario_id,
            user_verdict=user_verdict,
            judgment=judgment,
            is_correct=is_correct,
            answered_at=_utcnow(),
        )
        bundle.attempts.append(attempt)
        return attempt

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _find_scenario(self, bundle: AnalysisBundle, scenario_id: str) -> Scenario:
        for sc in bundle.scenario_set.scenarios:
            if sc.scenario_id == scenario_id:
                return sc
        raise ValueError(f"未找到情景 {scenario_id}")

    def _resolve_rules(self, bundle: AnalysisBundle, rule_ids: list[str]) -> list:
        by_id = {r.rule_id: r for r in bundle.rule_result.rules}
        return [by_id[rid] for rid in rule_ids if rid in by_id]

    def _related_sources_text(self, rules: list, by_id: dict[str, SourceBlock]) -> str:
        parts: list[str] = []
        seen: set[str] = set()
        for rule in rules:
            for cit in rule.citations:
                sid = cit.source_id
                if sid in seen:
                    continue
                block = by_id.get(sid)
                if block is None:
                    continue
                seen.add(sid)
                page = f"page={block.page_number}" if block.page_number else "page=NA"
                parts.append(f"[{block.source_id}|{page}] {block.text}")
        return "\n".join(parts) if parts else "（无关联来源）"

    @staticmethod
    def _renumber_rules(rule_result: RuleExtractionResult):
        id_map: dict[str, str] = {}
        new_rules = []
        for i, rule in enumerate(rule_result.rules, start=1):
            new_id = f"R{i:03d}"
            # 重复旧 ID 映射到第一次出现的新 ID（first-wins）
            if rule.rule_id not in id_map:
                id_map[rule.rule_id] = new_id
            new_rules.append(rule.model_copy(update={"rule_id": new_id}))
        return rule_result.model_copy(update={"rules": new_rules}), id_map

    @staticmethod
    def _renumber_scenarios(scenario_set: ScenarioSet, rule_id_map: dict[str, str]):
        new_scenarios = []
        for i, sc in enumerate(scenario_set.scenarios, start=1):
            new_id = f"C{i:03d}"
            related = [rule_id_map.get(rid, rid) for rid in sc.related_rule_ids]
            new_scenarios.append(
                sc.model_copy(update={"scenario_id": new_id, "related_rule_ids": related})
            )
        return scenario_set.model_copy(update={"scenarios": new_scenarios})

    @staticmethod
    def _renumber_issues(ambiguity: AmbiguityReport):
        new_issues = []
        for i, issue in enumerate(ambiguity.issues, start=1):
            new_issues.append(issue.model_copy(update={"issue_id": f"I{i:03d}"}))
        return ambiguity.model_copy(update={"issues": new_issues})

    @staticmethod
    def _verify_rule_citations(rule_result: RuleExtractionResult, by_id: dict[str, SourceBlock]):
        verifier = CitationVerifier()
        new_rules = []
        for rule in rule_result.rules:
            new_citations = verifier.verify(rule.citations, by_id)
            new_rules.append(rule.model_copy(update={"citations": new_citations}))
        return rule_result.model_copy(update={"rules": new_rules})

    @staticmethod
    def _verify_ambiguity_citations(ambiguity: AmbiguityReport, by_id: dict[str, SourceBlock]):
        verifier = CitationVerifier()
        new_issues = []
        for issue in ambiguity.issues:
            new_citations = verifier.verify(issue.citations, by_id)
            new_issues.append(issue.model_copy(update={"citations": new_citations}))
        return ambiguity.model_copy(update={"issues": new_issues})


def _rules_to_json(rules: list) -> str:
    from ..models import RuleExtractionResult

    return RuleExtractionResult(
        document_title="", document_summary="", rules=rules
    ).model_dump_json()
