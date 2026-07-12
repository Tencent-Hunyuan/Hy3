from __future__ import annotations

from copy import deepcopy

from apps.incident_agent.agent import (
    AgentMessage,
    AgentToolCall,
    investigate,
)


class FakeAgentClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, messages, tools=None):
        self.calls.append(
            {
                "messages": deepcopy(messages),
                "tools": deepcopy(tools),
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_investigation_runs_multi_round_tools_and_reports(tmp_path):
    (tmp_path / "service.py").write_text("value = 1\n", encoding="utf-8")
    client = FakeAgentClient(
        [
            AgentMessage(
                "I will inspect the files first.",
                (AgentToolCall("call-1", "list_files", "{}"),),
            ),
            AgentMessage(
                None,
                (
                    AgentToolCall(
                        "call-2",
                        "read_file",
                        '{"path":"service.py","start_line":1,"end_line":20}',
                    ),
                ),
            ),
            AgentMessage(
                "## Root cause\nThe evidence is in `service.py:1`.",
                (),
            ),
        ]
    )

    events = list(investigate("Find the fault", tmp_path, client))

    assert [event["type"] for event in events] == [
        "started",
        "plan",
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_result",
        "report",
        "done",
    ]
    assert events[3]["ok"] is True
    assert "service.py" in events[5]["content"]
    assert client.calls[1]["messages"][-1]["role"] == "tool"


def test_malformed_tool_json_becomes_failed_observation(tmp_path):
    client = FakeAgentClient(
        [
            AgentMessage(
                None,
                (AgentToolCall("broken", "read_file", "{not-json"),),
            ),
            AgentMessage("## Root cause\nThe tool arguments were invalid.", ()),
        ]
    )

    events = list(investigate("Inspect", tmp_path, client))

    result = next(event for event in events if event["type"] == "tool_result")
    assert result["ok"] is False
    assert "valid JSON" in result["content"]


def test_round_limit_forces_final_synthesis(tmp_path):
    client = FakeAgentClient(
        [
            AgentMessage(
                "Check the files.",
                (AgentToolCall("call-1", "list_files", "{}"),),
            ),
            AgentMessage("## Root cause\nRetry budget is off by one.", ()),
        ]
    )

    events = list(investigate("Inspect", tmp_path, client, max_rounds=1))

    assert any(event["type"] == "report" for event in events)
    assert client.calls[-1]["tools"] is None
    assert "synthesize" in client.calls[-1]["messages"][-1]["content"].lower()


def test_upstream_failure_is_sanitized(tmp_path):
    client = FakeAgentClient([RuntimeError("secret provider response")])

    events = list(investigate("Inspect", tmp_path, client))

    error = next(event for event in events if event["type"] == "error")
    assert error["message"] == "Hy3 investigation failed. Check the API and retry."
    assert "secret provider response" not in str(events)
    assert events[-1]["type"] == "done"


def test_empty_hy3_response_is_retried_before_error(tmp_path):
    client = FakeAgentClient(
        [
            AgentMessage(None, ()),
            AgentMessage("## Root cause\nThe retry loop is off by one.", ()),
        ]
    )

    events = list(investigate("Inspect", tmp_path, client))

    assert len(client.calls) == 2
    assert any(event["type"] == "report" for event in events)
    assert not any(event["type"] == "error" for event in events)
