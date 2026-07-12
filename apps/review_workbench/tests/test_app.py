from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.review_workbench.app import app, get_hy3_client


class FakeHy3Client:
    def complete(self, prompt: str) -> str:
        assert "+ risky_change()" in prompt
        return "## Summary\nHy3 result"


class FailingHy3Client:
    def complete(self, prompt: str) -> str:
        raise RuntimeError("secret upstream details")


class TimeoutHy3Client:
    def complete(self, prompt: str) -> str:
        raise TimeoutError("upstream took too long")


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def client(completion_client=None) -> TestClient:
    app.dependency_overrides[get_hy3_client] = lambda: completion_client or FakeHy3Client()
    return TestClient(app)


def test_review_calls_hy3_and_returns_metadata():
    response = client().post(
        "/api/review",
        json={
            "patch_text": "+ risky_change()",
            "language": "python",
            "focus": "security",
            "context": "Payment service",
        },
    )

    assert response.status_code == 200
    assert response.json()["content"] == "## Summary\nHy3 result"
    assert response.json()["metadata"]["language"] == "python"
    assert response.json()["metadata"]["duration_ms"] >= 0


def test_test_plan_calls_hy3():
    response = client().post(
        "/api/tests",
        json={
            "diff_text": "+ risky_change()",
            "test_framework": "pytest",
            "risk_level": "high",
        },
    )

    assert response.status_code == 200
    assert response.json()["content"].startswith("## Summary")
    assert response.json()["metadata"]["test_framework"] == "pytest"


def test_empty_and_oversized_diffs_are_rejected():
    test_client = client()

    assert test_client.post("/api/review", json={"patch_text": "   "}).status_code == 422
    response = test_client.post("/api/review", json={"patch_text": "+" * 24_001})
    assert response.status_code == 422


def test_status_never_exposes_api_key(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("HY3_API_KEY", "super-secret")
    monkeypatch.setenv("HY3_MODEL", "hy3")

    response = client().get("/api/status")

    assert response.status_code == 200
    assert response.json() == {
        "ready": True,
        "model": "hy3",
        "endpoint": "gateway.example",
    }
    assert "super-secret" not in response.text


def test_upstream_errors_are_sanitized():
    response = client(FailingHy3Client()).post(
        "/api/review",
        json={"patch_text": "+ change"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Hy3 request failed. Check the endpoint and try again."
    )
    assert "secret upstream details" not in response.text


def test_upstream_timeouts_return_gateway_timeout():
    response = client(TimeoutHy3Client()).post(
        "/api/review",
        json={"patch_text": "+ change"},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "Hy3 request timed out. Try again."


def test_external_endpoint_without_api_key_returns_setup_error(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("HY3_API_KEY", "EMPTY")
    monkeypatch.setenv("HY3_MODEL", "hy3")

    response = TestClient(app).post(
        "/api/review",
        json={"patch_text": "+ change"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Hy3 API is not configured. Add credentials to .env and retry."
    )


def test_examples_support_both_demo_flows():
    response = client().get("/api/examples")

    assert response.status_code == 200
    examples = response.json()
    assert [item["id"] for item in examples] == [
        "payment-security",
        "retry-reliability",
    ]
    assert {item["mode"] for item in examples} == {"review", "tests"}
    assert all(item["diff_text"].startswith("diff --git") for item in examples)


def test_root_serves_workbench_without_secrets(monkeypatch):
    monkeypatch.setenv("HY3_API_KEY", "never-render-this")

    response = client().get("/")

    assert response.status_code == 200
    assert "Hy3 Review Workbench" in response.text
    assert 'id="diff-input"' in response.text
    assert 'id="run-button"' in response.text
    assert "never-render-this" not in response.text


def test_static_assets_are_served():
    test_client = client()

    assert test_client.get("/static/styles.css").status_code == 200
    script = test_client.get("/static/app.js")
    assert script.status_code == 200
    assert "submitAnalysis" in script.text


def test_app_readme_documents_required_submission_details():
    readme = Path("apps/review_workbench/README.md").read_text(encoding="utf-8")
    required = [
        "Hy3's role",
        "Demo 1",
        "Demo 2",
        "CodeBuddy collaboration",
        "uvicorn apps.review_workbench.app:app",
    ]

    assert all(item in readme for item in required)
