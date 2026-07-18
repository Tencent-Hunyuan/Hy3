from pathlib import PurePosixPath

import pytest
from pydantic import ValidationError

from hy3_knowledge_mcp.citations import validate_answer_payload
from hy3_knowledge_mcp.errors import CitationValidationError
from hy3_knowledge_mcp.models import Evidence, Hy3AnswerPayload, Hy3SummaryPayload


def evidence(identifier: str) -> Evidence:
    return Evidence(
        evidence_id=identifier,
        chunk_id=int(identifier[1:]),
        source_path=PurePosixPath(f"root/{identifier}.md"),
        text=f"evidence {identifier}",
        line_start=1,
        line_end=2,
    )


def test_valid_citations_are_resolved_and_deduplicated() -> None:
    result = validate_answer_payload(
        Hy3AnswerPayload(
            answer="Grounded answer",
            used_evidence_ids=("S2", "S1", "S2"),
            insufficient_evidence=False,
        ),
        (evidence("S1"), evidence("S2")),
    )

    assert result.grounded is True
    assert [item.evidence_id for item in result.citations] == ["S2", "S1"]


def test_duplicate_supplied_evidence_ids_are_rejected() -> None:
    with pytest.raises(CitationValidationError):
        validate_answer_payload(
            Hy3AnswerPayload(
                answer="Grounded answer",
                used_evidence_ids=("S1",),
                insufficient_evidence=False,
            ),
            (evidence("S1"), evidence("S1")),
        )


def test_unknown_evidence_id_is_rejected_without_leaking_context() -> None:
    with pytest.raises(CitationValidationError) as captured:
        validate_answer_payload(
            Hy3AnswerPayload(
                answer="Bad answer",
                used_evidence_ids=("S9",),
                insufficient_evidence=False,
            ),
            (evidence("S1"),),
        )

    assert captured.value.__cause__ is None
    assert "S9" not in str(captured.value)
    assert "root/S1.md" not in str(captured.value)


def test_payload_rejects_malformed_evidence_ids() -> None:
    with pytest.raises(ValidationError):
        Hy3AnswerPayload(
            answer="Answer",
            used_evidence_ids=("not-an-evidence-id",),
            insufficient_evidence=False,
        )

    with pytest.raises(ValidationError):
        Hy3SummaryPayload(summary="Summary", used_evidence_ids=("S0",))


def test_grounded_answer_requires_at_least_one_citation() -> None:
    with pytest.raises(CitationValidationError):
        validate_answer_payload(
            Hy3AnswerPayload(
                answer="No citation",
                used_evidence_ids=(),
                insufficient_evidence=False,
            ),
            (evidence("S1"),),
        )


def test_insufficient_answer_may_have_no_citations() -> None:
    result = validate_answer_payload(
        Hy3AnswerPayload(
            answer="The knowledge base does not contain enough evidence.",
            used_evidence_ids=(),
            insufficient_evidence=True,
        ),
        (evidence("S1"),),
    )

    assert result.grounded is False
    assert result.citations == ()


def test_insufficient_answer_may_retain_known_citations_without_being_grounded() -> None:
    result = validate_answer_payload(
        Hy3AnswerPayload(
            answer="The available evidence is incomplete.",
            used_evidence_ids=("S1",),
            insufficient_evidence=True,
        ),
        (evidence("S1"),),
    )

    assert result.grounded is False
    assert [item.evidence_id for item in result.citations] == ["S1"]


def test_insufficient_answer_still_rejects_unknown_evidence_ids() -> None:
    with pytest.raises(CitationValidationError):
        validate_answer_payload(
            Hy3AnswerPayload(
                answer="The available evidence is incomplete.",
                used_evidence_ids=("S9",),
                insufficient_evidence=True,
            ),
            (evidence("S1"),),
        )


@pytest.mark.parametrize("answer", ["", " \n\t "])
def test_answer_payload_rejects_empty_answer(answer: str) -> None:
    with pytest.raises(ValidationError):
        Hy3AnswerPayload(
            answer=answer,
            used_evidence_ids=(),
            insufficient_evidence=True,
        )


@pytest.mark.parametrize("summary", ["", " \n\t "])
def test_summary_payload_rejects_empty_summary(summary: str) -> None:
    with pytest.raises(ValidationError):
        Hy3SummaryPayload(summary=summary, used_evidence_ids=())
