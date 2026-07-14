"""Streamlit UI 组件与编排。

所有模型调用期间显示阶段性进度，不显示假的百分比。
业务层（AnalysisService / ExportService）不依赖 Streamlit，可独立测试。
"""

from __future__ import annotations

import streamlit as st

from ..config import load_settings
from ..exceptions import RuleLensError
from ..llm.hy3_client import Hy3Client
from ..models import AnalysisBundle, CitationStatus, IssueType, Verdict
from ..services import AnalysisService, to_json, to_markdown
from ..services.export_service import build_export_filename
from .state import Stage, get_state, init_state, load_file, reset_state

SAMPLES_DIR = __import__("pathlib").Path(__file__).resolve().parents[3] / "data" / "samples"

VERDICT_LABELS = {
    Verdict.COMPLIANT: "符合",
    Verdict.NON_COMPLIANT: "不符合",
    Verdict.INSUFFICIENT_INFO: "信息不足",
}

ISSUE_TYPE_LABELS = {
    IssueType.AMBIGUOUS_TERM: "术语模糊",
    IssueType.CONFLICT: "条款冲突",
    IssueType.MISSING_BOUNDARY: "边界缺失",
    IssueType.MISSING_PROCEDURE: "流程缺失",
    IssueType.MISSING_EXCEPTION: "例外缺失",
    IssueType.UNVERIFIABLE: "不可验证",
    IssueType.REDUNDANT: "重复冗余",
}

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def render_app() -> None:
    init_state()
    st.set_page_config(page_title="RuleLens · 规则透镜", page_icon="🔍", layout="wide")

    st.title("RuleLens · 规则透镜")
    st.caption("把规则文档变成可验证的边界案例")

    _render_sidebar()

    state = get_state()
    stage = state.stage

    if stage in (Stage.EMPTY, Stage.EXTRACTED) or state.bundle is None:
        _render_initial()
    else:
        _render_results(state.bundle)


# --------------------------------------------------------------------------- #
# 侧边栏
# --------------------------------------------------------------------------- #
def _render_sidebar() -> None:
    settings = load_settings()
    state = get_state()

    with st.sidebar:
        st.header("状态")
        if settings.is_configured:
            st.success("✅ Hy3 API 已配置")
            with st.expander("配置摘要"):
                summary = settings.public_summary()
                st.markdown(f"- 模型：`{summary['model']}`")
                st.markdown(f"- 端点：`{summary['base_url']}`")
                st.markdown(f"- 密钥：`{summary['api_key']}`")
                st.markdown(f"- 推理强度：`{summary['reasoning_effort']}`")
        else:
            st.error("⚠️ Hy3 API 未配置")
            st.markdown("请复制 `.env.example` 为 `.env` 并填入 Hy3 API 配置。")

        st.divider()
        st.header("文档信息")
        if state.file_name:
            st.markdown(f"- 文件：`{state.file_name}`")
            st.markdown(f"- SHA256：`{str(state.file_sha256)[:12]}…`")
        else:
            st.markdown("- 尚未载入文档")

        st.divider()
        st.header("进度")
        bundle = state.bundle
        if bundle is not None:
            total = len(bundle.scenario_set.scenarios)
            answered = len({a.scenario_id for a in bundle.attempts})
            correct = sum(1 for a in bundle.attempts if a.is_correct)
            st.markdown(f"- 阶段：`{state.stage}`")
            st.markdown(f"- 答题：{answered}/{total}")
            st.markdown(f"- 当前得分：{correct}/{total}")
        else:
            st.markdown("- 阶段：`EMPTY`")

        st.divider()
        if st.button("🔄 重置", key="sidebar_reset", use_container_width=True):
            _do_reset()

        st.divider()
        st.caption(
            "⚠️ 免责声明：本工具由 AI 辅助生成，不构成法律、合规或专业意见。"
            "上传的文档会发送到配置的 Hy3 API，默认不做持久化保存。"
        )


def _do_reset() -> None:
    reset_state()
    # 清空文件上传控件
    st.session_state.pop("uploader", None)
    st.rerun()


# --------------------------------------------------------------------------- #
# 初始页
# --------------------------------------------------------------------------- #
def _render_initial() -> None:
    state = get_state()
    settings = load_settings()

    st.header("上传规则文档")
    uploaded = st.file_uploader(
        "支持 PDF / Markdown / TXT（单文件，最多 10MB，提取后最多 100,000 字符）",
        type=["pdf", "md", "txt", "markdown"],
        key="uploader",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.button(
            "📘 载入比赛规则示例",
            key="sample_contest",
            use_container_width=True,
            on_click=lambda: st.session_state.__setitem__("_pending_sample", "contest"),
        )
    with col2:
        st.button(
            "📗 载入课程制度示例",
            key="sample_course",
            use_container_width=True,
            on_click=lambda: st.session_state.__setitem__("_pending_sample", "course"),
        )

    # 处理示例载入
    pending = st.session_state.get("_pending_sample")
    if pending:
        _load_sample(pending)
        st.session_state["_pending_sample"] = None
        st.rerun()

    # 处理上传
    if uploaded is not None:
        data = uploaded.getvalue()
        if state.file_name != uploaded.name or state.file_sha256 != _sha_of(data):
            load_file(uploaded.name, data)
            st.rerun()

    can_analyze = state.file_bytes is not None
    st.divider()

    st.info(
        "🔒 隐私提示：文档内容会发送到你在 `.env` 中配置的 Hy3 API，"
        "应用默认不做持久化保存。请勿上传机密文件。"
    )

    if not settings.is_configured:
        st.warning(
            "尚未配置 Hy3 API，请先在 `.env` 中填写 HY3_API_KEY / HY3_BASE_URL / HY3_MODEL。"
        )
        return

    if st.button(
        "🚀 开始分析",
        key="start_analysis",
        type="primary",
        disabled=not can_analyze,
        use_container_width=True,
    ):
        _run_analysis()


def _sha_of(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _load_sample(kind: str) -> None:
    file_name = "demo_contest_rules.md" if kind == "contest" else "demo_course_policy.md"
    path = SAMPLES_DIR / file_name
    if not path.exists():
        st.error(f"示例文件缺失：{path}")
        return
    load_file(file_name, path.read_bytes())


def _run_analysis() -> None:
    state = get_state()
    settings = load_settings()
    service = AnalysisService(Hy3Client(settings), settings)

    try:
        with st.status("正在分析文档…", expanded=True) as status:
            bundle = service.analyze_document(
                state.file_name, state.file_bytes, progress=status.write
            )
            status.update(label="✅ 分析完成", state="complete", expanded=False)
        state.bundle = bundle
        state.stage = Stage.ANALYZED
        st.rerun()
    except RuleLensError as exc:
        state.last_error = exc.user_message
        st.error(exc.user_message)
    except Exception:  # noqa: BLE001 - 不向页面暴露堆栈
        state.last_error = "分析过程中出现未知错误，请稍后重试。"
        st.error("分析过程中出现未知错误，请稍后重试。")


# --------------------------------------------------------------------------- #
# 结果页
# --------------------------------------------------------------------------- #
def _render_results(bundle: AnalysisBundle) -> None:
    _render_summary(bundle)
    tabs = st.tabs(["🗺️ 规则地图", "🎯 情景闯关", "📡 歧义雷达", "📄 原文", "⬇️ 导出"])
    with tabs[0]:
        _render_rules_tab(bundle)
    with tabs[1]:
        _render_quiz_tab(bundle)
    with tabs[2]:
        _render_ambiguity_tab(bundle)
    with tabs[3]:
        _render_source_tab(bundle)
    with tabs[4]:
        _render_export_tab(bundle)


def _render_summary(bundle: AnalysisBundle) -> None:
    rules_n = len(bundle.rule_result.rules)
    scen_n = len(bundle.scenario_set.scenarios)
    issues_n = len(bundle.ambiguity_report.issues)
    verified, total = _citation_stats(bundle)
    rate = f"{(verified / total * 100):.0f}%" if total else "N/A"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("识别规则", rules_n)
    c2.metric("生成情景", scen_n)
    c3.metric("潜在问题", issues_n)
    c4.metric("引用核验通过率", rate)

    if bundle.rule_result.document_summary:
        with st.expander("文档摘要", expanded=False):
            st.write(bundle.rule_result.document_summary)
    if bundle.rule_result.defined_terms:
        with st.expander("已定义术语", expanded=False):
            for term, definition in bundle.rule_result.defined_terms.items():
                st.markdown(f"- **{term}**：{definition}")


# --------------------------------------------------------------------------- #
# Tab A：规则地图
# --------------------------------------------------------------------------- #
def _render_rules_tab(bundle: AnalysisBundle) -> None:
    by_id = {s.source_id: s for s in bundle.sources}
    topics: dict[str, list] = {}
    for rule in bundle.rule_result.rules:
        topics.setdefault(rule.topic or "未分类", []).append(rule)

    for topic, rules in topics.items():
        st.subheader(topic)
        for rule in rules:
            with st.container(border=True):
                st.markdown(
                    f"**{rule.rule_id} · {rule.title}**  "
                    f"`{rule.rule_type.value}`  "
                    f"置信度 {rule.confidence:.2f}"
                )
                st.markdown(f"> {rule.normalized_statement}")
                if rule.conditions:
                    st.markdown("**条件**：" + "；".join(rule.conditions))
                if rule.exceptions:
                    st.markdown("**例外**：" + "；".join(rule.exceptions))
                if rule.consequences:
                    st.markdown("**后果**：" + "；".join(rule.consequences))
                if rule.related_rule_ids:
                    st.caption("关联规则：" + ", ".join(rule.related_rule_ids))
                for cit in rule.citations:
                    _render_citation(cit, by_id)


# --------------------------------------------------------------------------- #
# Tab B：情景闯关
# --------------------------------------------------------------------------- #
def _render_quiz_tab(bundle: AnalysisBundle) -> None:
    state = get_state()
    scenarios = bundle.scenario_set.scenarios
    total = len(scenarios)
    attempts = {a.scenario_id: a for a in bundle.attempts}

    if total == 0:
        st.info("未生成任何情景。")
        return

    idx = state.current_scenario_index
    if idx >= total:
        idx = total - 1
        state.current_scenario_index = idx

    scenario = scenarios[idx]
    answered = scenario.scenario_id in attempts

    st.markdown(f"### 第 {idx + 1} / {total} 题 · {scenario.title}")
    st.caption(f"边界类型：{scenario.boundary_type} ｜ 难度：{scenario.difficulty}")
    st.write(scenario.description)

    nav_col1, nav_col2, _ = st.columns([1, 1, 3])
    with nav_col1:
        if st.button("◀ 上一题", disabled=idx == 0, key="quiz_prev"):
            state.current_scenario_index = max(0, idx - 1)
            st.rerun()
    with nav_col2:
        if st.button("下一题 ▶", disabled=idx >= total - 1, key="quiz_next"):
            state.current_scenario_index = min(total - 1, idx + 1)
            st.rerun()

    if not answered:
        cols = st.columns(3)
        with cols[0]:
            if st.button("✅ 符合", key="v_compliant", use_container_width=True):
                _submit_answer(bundle, scenario.scenario_id, Verdict.COMPLIANT)
        with cols[1]:
            if st.button("❌ 不符合", key="v_noncompliant", use_container_width=True):
                _submit_answer(bundle, scenario.scenario_id, Verdict.NON_COMPLIANT)
        with cols[2]:
            if st.button("❓ 信息不足", key="v_insufficient", use_container_width=True):
                _submit_answer(bundle, scenario.scenario_id, Verdict.INSUFFICIENT_INFO)
    else:
        _render_attempt(bundle, attempts[scenario.scenario_id])

    answered_n = len(attempts)
    if answered_n == total:
        correct = sum(1 for a in attempts.values() if a.is_correct)
        st.success(f"🎉 已完成全部 {total} 题，得分 {correct}/{total}。")
        state.stage = Stage.COMPLETED
    elif attempts:
        state.stage = Stage.QUIZ_ACTIVE


def _submit_answer(bundle: AnalysisBundle, scenario_id: str, verdict: Verdict) -> None:
    settings = load_settings()
    service = AnalysisService(Hy3Client(settings), settings)
    try:
        with st.status("正在裁决…", expanded=False) as status:
            service.judge_scenario(bundle, scenario_id, verdict)
            status.update(label="✅ 已裁决", state="complete", expanded=False)
        # 答题结果已写入 bundle.attempts，重新渲染即可更新进度与解释
        st.rerun()
    except RuleLensError as exc:
        st.error(exc.user_message)
    except Exception:  # noqa: BLE001
        st.error("裁决过程中出现未知错误，请稍后重试。")


def _render_attempt(bundle: AnalysisBundle, attempt) -> None:
    by_id = {s.source_id: s for s in bundle.sources}
    j = attempt.judgment
    mark = "✅ 回答正确" if attempt.is_correct else "❌ 回答有误"
    st.markdown(
        f"**你的判断**：{VERDICT_LABELS.get(attempt.user_verdict, attempt.user_verdict.value)} ｜ {mark}"
    )
    st.markdown(f"**正确结论**：`{j.verdict.value}`")
    st.info(f"**判断依据摘要**：{j.rationale_summary}")
    if j.applied_rule_ids:
        st.markdown("**适用规则**：" + ", ".join(j.applied_rule_ids))
    if j.missing_information:
        st.markdown("**缺失信息**：" + "；".join(j.missing_information))
    st.markdown("**原文证据**：")
    for cit in j.citations:
        _render_citation(cit, by_id)


# --------------------------------------------------------------------------- #
# Tab C：歧义雷达
# --------------------------------------------------------------------------- #
def _render_ambiguity_tab(bundle: AnalysisBundle) -> None:
    by_id = {s.source_id: s for s in bundle.sources}
    st.warning("⚠️ 这是 AI 辅助审阅结果，不构成法律或合规意见。")

    issues = sorted(
        bundle.ambiguity_report.issues,
        key=lambda i: SEVERITY_ORDER.get(i.severity, 9),
    )
    if not issues:
        st.success("未检测到明显歧义或冲突。")
        return

    for issue in issues:
        color = {"HIGH": "red", "MEDIUM": "orange", "LOW": "green"}.get(issue.severity, "gray")
        with st.container(border=True):
            st.markdown(
                f"**{issue.issue_id} · {issue.title}**  "
                f"`{issue.issue_type.value}`  "
                f":{color}[严重程度 {issue.severity}]  置信度 {issue.confidence:.2f}"
            )
            st.markdown(f"- **说明**：{issue.description}")
            st.markdown(f"- **可能影响**：{issue.impact}")
            st.markdown(f"- **建议修改**：{issue.suggestion}")
            if issue.citations:
                st.markdown("**涉及来源**：")
                for cit in issue.citations:
                    _render_citation(cit, by_id)


# --------------------------------------------------------------------------- #
# Tab D：原文
# --------------------------------------------------------------------------- #
def _render_source_tab(bundle: AnalysisBundle) -> None:
    with st.expander("查看带来源编号的提取文本", expanded=False):
        query = st.text_input("按来源编号搜索（如 S0001）", key="source_search")
        for block in bundle.sources:
            if query and query.upper() not in block.source_id.upper():
                continue
            page = f"第 {block.page_number} 页" if block.page_number else "无页码"
            st.markdown(f"**[{block.source_id} | {page}]**")
            st.text(block.text)


# --------------------------------------------------------------------------- #
# Tab E：导出
# --------------------------------------------------------------------------- #
def _render_export_tab(bundle: AnalysisBundle) -> None:
    col1, col2 = st.columns(2)
    with col1:
        md = to_markdown(bundle)
        st.download_button(
            "⬇️ 下载 Markdown 报告",
            data=md,
            file_name=build_export_filename(bundle.file_name, "md"),
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        js = to_json(bundle)
        st.download_button(
            "⬇️ 下载 JSON 数据",
            data=js,
            file_name=build_export_filename(bundle.file_name, "json"),
            mime="application/json",
            use_container_width=True,
        )
    st.caption(
        "导出内容包含文档哈希、分析时间、模型名、规则、情景裁决、歧义与引用核验状态，"
        "不包含 API 密钥或隐藏思维链。"
    )


# --------------------------------------------------------------------------- #
# 引用渲染
# --------------------------------------------------------------------------- #
def _render_citation(cit, by_id: dict) -> None:
    status = cit.status
    if status == CitationStatus.VERIFIED:
        tag = ":green[✅ 原文已核验]"
    elif status == CitationStatus.SOURCE_ONLY:
        tag = ":orange[🟡 来源存在，未核验短引文]"
    elif status == CitationStatus.FAILED:
        tag = ":red[🔴 引用需人工复核]"
    else:
        tag = "N/A"

    block = by_id.get(cit.source_id)
    quote = cit.evidence_quote or "（模型未返回可核验短引文）"
    label = f"`{cit.source_id}` {tag}"
    if block is None:
        st.markdown(f"{label} — 来源不存在")
        st.caption(quote)
        return
    with st.expander(label, expanded=False):
        st.caption("模型短引文：" + quote)
        page = f"第 {block.page_number} 页 · " if block.page_number else ""
        st.markdown(f"**原文（{page}{cit.source_id}）**：")
        st.text(block.text)


# --------------------------------------------------------------------------- #
# 引用统计
# --------------------------------------------------------------------------- #
def _citation_stats(bundle: AnalysisBundle) -> tuple[int, int]:
    verified = 0
    total = 0
    for rule in bundle.rule_result.rules:
        for c in rule.citations:
            total += 1
            if c.status == CitationStatus.VERIFIED:
                verified += 1
    for issue in bundle.ambiguity_report.issues:
        for c in issue.citations:
            total += 1
            if c.status == CitationStatus.VERIFIED:
                verified += 1
    for attempt in bundle.attempts:
        for c in attempt.judgment.citations:
            total += 1
            if c.status == CitationStatus.VERIFIED:
                verified += 1
    return verified, total
