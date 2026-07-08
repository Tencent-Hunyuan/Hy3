from hy3_mcp_server.hy3_client import Hy3Client, Hy3Settings
from hy3_mcp_server.tools import answer_question, inspect_data, normalize_documents, review_diff


def mock_client() -> Hy3Client:
    return Hy3Client(Hy3Settings(base_url="http://127.0.0.1:8000/v1", api_key="", mock=True))


def test_review_diff_returns_tool_payload() -> None:
    result = review_diff("+ return user.name\n", client=mock_client())

    assert result["tool"] == "hy3_code_review"
    assert "Mock Hy3 response" in result["result"]


def test_document_qa_normalizes_document_ids() -> None:
    docs = normalize_documents([{"title": "Readme", "text": "Hy3 API"}])

    assert docs == [{"id": "doc-1", "title": "Readme", "text": "Hy3 API"}]


def test_answer_question_counts_documents() -> None:
    result = answer_question(
        "What is Hy3 used for?",
        [{"id": "a", "title": "A", "text": "Hy3 powers reasoning."}],
        client=mock_client(),
    )

    assert result["document_count"] == 1


def test_inspect_data_profiles_csv() -> None:
    result = inspect_data("name,score\nalpha,1\nbeta,\n", client=mock_client())

    assert result["profile"]["format"] == "csv"
    assert result["profile"]["row_count"] == 2
    assert result["profile"]["null_counts"]["score"] == 1
