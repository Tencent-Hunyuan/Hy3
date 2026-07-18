"""证据 ID 与引用校验。"""

from .errors import CitationValidationError
from .models import AskResult, Citation, Evidence, Hy3AnswerPayload


def _citation(item: Evidence) -> Citation:
    """把已供应证据转换为公开引用。"""
    return Citation(
        evidence_id=item.evidence_id,
        source_path=item.source_path,
        page_number=item.page_number,
        line_start=item.line_start,
        line_end=item.line_end,
    )


def validate_evidence_ids(
    identifiers: tuple[str, ...],
    evidence: tuple[Evidence, ...],
) -> tuple[Citation, ...]:
    """仅解析实际供应给模型的证据 ID。保留首次出现顺序。"""
    by_id = {item.evidence_id: item for item in evidence}
    if len(by_id) != len(evidence):
        raise CitationValidationError("供应的证据 ID 必须唯一")
    if any(identifier not in by_id for identifier in identifiers):
        raise CitationValidationError("Hy3 引用了未供应的证据。请重试工具调用")
    ordered_unique = tuple(dict.fromkeys(identifiers))
    return tuple(_citation(by_id[identifier]) for identifier in ordered_unique)


def validate_answer_payload(
    payload: Hy3AnswerPayload,
    evidence: tuple[Evidence, ...],
) -> AskResult:
    """验证 Hy3 回答载荷只引用已供应证据。"""
    citations = validate_evidence_ids(payload.used_evidence_ids, evidence)
    if not payload.insufficient_evidence and not citations:
        raise CitationValidationError("有依据的 Hy3 回答必须至少引用一条已供应证据")
    return AskResult(
        answer=payload.answer,
        grounded=not payload.insufficient_evidence and bool(citations),
        insufficient_evidence=payload.insufficient_evidence,
        citations=citations,
    )
