from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.incident_agent.agent import AgentMessage
from apps.incident_agent.app import app, get_configured_agent_client


class FakeAgentClient:
    def __init__(self):
        self.calls = []

    def complete(self, messages, tools=None):
        self.calls.append({"messages": messages, "tools": tools})
        return AgentMessage(
            "## Root cause\nThe retry budget is off by one.\n\n"
            "## Evidence\n`client.py:7` uses `retries + 1`.\n\n"
            "## Remediation\nUse `range(retries)`.\n\n"
            "## Verification\nRun pytest.",
            (),
        )


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def client(agent_client=None) -> TestClient:
    app.dependency_overrides[get_configured_agent_client] = lambda: (
        agent_client or FakeAgentClient()
    )
    return TestClient(app)


def test_demos_are_public_without_file_contents():
    response = client().get("/api/demos")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        "retry-regression",
        "worker-startup",
    ]
    assert "files" not in response.text


def test_demo_investigation_streams_ndjson():
    response = client().post(
        "/api/investigate",
        data={"task": "Find the regression", "demo_id": "retry-regression"},
    )

    events = [json.loads(line) for line in response.text.splitlines()]
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert events[0]["type"] == "started"
    assert events[-1] == {"type": "done", "status": "completed"}
    assert any(event["type"] == "report" for event in events)


def test_uploaded_file_can_be_investigated():
    response = client().post(
        "/api/investigate",
        data={"task": "Inspect this service"},
        files={"files": ("service.py", b"value = 1\n", "text/x-python")},
    )

    assert response.status_code == 200
    assert '"type": "report"' in response.text


def test_upload_validation_happens_before_streaming():
    response = client().post(
        "/api/investigate",
        data={"task": "Inspect this"},
        files={"files": ("unsafe.exe", b"binary", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")


def test_blank_task_and_unknown_demo_are_rejected():
    test_client = client()

    blank = test_client.post(
        "/api/investigate",
        data={"task": "   "},
        files={"files": ("service.py", b"value = 1\n", "text/x-python")},
    )
    unknown = test_client.post(
        "/api/investigate",
        data={"task": "Inspect", "demo_id": "missing"},
    )

    assert blank.status_code == 422
    assert unknown.status_code == 422


def test_status_never_exposes_api_key(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("HY3_API_KEY", "agent-secret")
    monkeypatch.setenv("HY3_MODEL", "hy3")

    response = client().get("/api/status")

    assert response.json() == {
        "ready": True,
        "model": "hy3",
        "endpoint": "gateway.example",
    }
    assert "agent-secret" not in response.text
