"""Offline tests for the Repo Scout model/tool orchestration loop."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from hy3_repo_scout.agent import RepoScoutAgent  # noqa: E402
from hy3_repo_scout.config import Settings  # noqa: E402


def tool_call(call_id: str, name: str, arguments: str) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def completion(
    content: str | None,
    *,
    tool_calls: list[dict[str, Any]] | None = None,
    prompt_tokens: int = 3,
    completion_tokens: int = 2,
    finish_reason: str = "stop",
    reasoning_details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls or [],
                    "reasoning_details": reasoning_details,
                },
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


class FakeCompletions:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[dict[str, Any]] = []

    def create(self, **request: Any) -> Any:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.completions = FakeCompletions(outcomes)
        self.chat = type("Chat", (), {"completions": self.completions})()


class FakeTools:
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    def __init__(self) -> None:
        self.root = "/repo"
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.files_read: set[str] = set()

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        if name == "read_file":
            path = str(arguments["path"])
            self.files_read.add(path)
            return {
                "path": path,
                "start_line": 1,
                "end_line": 2,
                "content": "alpha\nbeta",
                "_evidence": [
                    {"path": path, "line": 1, "sha256": "a" * 64},
                    {"path": path, "line": 2, "sha256": "b" * 64},
                ],
            }
        return {"matches": [{"path": "README.md", "line": 1}]}


class FakeServerError(RuntimeError):
    status_code = 503


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "api_key": "test-key",
        "max_attempts": 1,
        "retry_base_delay": 0.0,
        "retry_max_delay": 0.0,
    }
    values.update(overrides)
    return Settings(**values)


class AgentLoopTests(unittest.TestCase):
    def test_multi_round_tool_loop_returns_report_trace_and_stats(self) -> None:
        first = completion(
            None,
            tool_calls=[
                tool_call("read-1", "read_file", '{"path":"README.md"}'),
                tool_call("search-1", "search_text", '{"query":"Hy3"}'),
            ],
            prompt_tokens=10,
            completion_tokens=4,
            finish_reason="tool_calls",
            reasoning_details=[{"type": "reasoning.text", "text": "inspect evidence"}],
        )
        second = completion(
            "# Executive Summary\nFound evidence [README.md:L1-L2].",
            prompt_tokens=20,
            completion_tokens=8,
        )
        client = FakeClient([first, second])
        tools = FakeTools()
        events: list[dict[str, Any]] = []

        result = RepoScoutAgent(
            settings(), tools, client=client, on_event=events.append
        ).run("Where is Hy3 documented?")

        self.assertEqual(result.rounds, 2)
        self.assertEqual(result.tool_calls, 2)
        self.assertEqual(result.files_read, 1)
        self.assertEqual(result.file_paths, ("README.md",))
        self.assertGreater(result.context_chars, 0)
        self.assertEqual(result.usage["prompt_tokens"], 30)
        self.assertEqual(result.usage["completion_tokens"], 12)
        self.assertEqual(result.usage["total_tokens"], 42)
        self.assertEqual([item.name for item in result.trace], ["read_file", "search_text"])
        self.assertEqual(len(result.trace[0].evidence), 2)
        self.assertIn("README.md:L1-L2", result.content)

        first_request = client.completions.requests[0]
        self.assertEqual(first_request["model"], "tencent/hy3:free")
        self.assertEqual(first_request["tool_choice"], "auto")
        self.assertEqual(
            first_request["extra_body"],
            {"reasoning": {"effort": "high"}},
        )
        second_messages = client.completions.requests[1]["messages"]
        self.assertEqual(
            second_messages[-3]["reasoning_details"],
            [{"type": "reasoning.text", "text": "inspect evidence"}],
        )
        self.assertEqual(second_messages[-2]["tool_call_id"], "read-1")
        self.assertEqual(second_messages[-1]["tool_call_id"], "search-1")
        self.assertNotIn("_evidence", second_messages[-2]["content"])
        self.assertEqual(events[0]["type"], "model_request")
        self.assertEqual(events[-1]["type"], "completed")

    def test_transient_model_failure_retries_and_emits_event(self) -> None:
        client = FakeClient([FakeServerError("busy"), completion("done")])
        events: list[dict[str, Any]] = []

        result = RepoScoutAgent(
            settings(max_attempts=2),
            FakeTools(),
            client=client,
            on_event=events.append,
        ).run("Summarize the repository")

        self.assertEqual(result.content, "done")
        self.assertEqual(len(client.completions.requests), 2)
        retries = [event for event in events if event["type"] == "retry"]
        self.assertEqual(len(retries), 1)
        self.assertEqual(retries[0]["attempt"], 1)
        self.assertEqual(retries[0]["error"], "FakeServerError")

    def test_tool_and_context_budgets_are_hard_limits(self) -> None:
        first = completion(
            None,
            tool_calls=[
                tool_call("one", "read_file", '{"path":"README.md"}'),
                tool_call("two", "read_file", '{"path":"README_CN.md"}'),
            ],
        )
        client = FakeClient([first, completion("bounded report")])
        tools = FakeTools()

        result = RepoScoutAgent(
            settings(
                max_tool_calls=1,
                max_context_chars=20,
                max_tool_result_chars=256,
            ),
            tools,
            client=client,
        ).run("Read both files")

        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(len(tools.calls), 1)
        self.assertEqual(result.context_chars, 20)
        self.assertEqual(len(result.trace), 2)
        self.assertTrue(result.trace[0].truncated)
        self.assertEqual(
            json.loads(result.trace[0].result)["error"]["code"],
            "context_budget",
        )
        self.assertIn("tool-call budget", result.trace[1].error or "")
        self.assertTrue(result.budget_exhausted)

    def test_aggregate_context_truncation_alone_marks_budget_exhausted(self) -> None:
        first = completion(
            None,
            tool_calls=[tool_call("one", "read_file", '{"path":"README.md"}')],
        )
        result = RepoScoutAgent(
            settings(max_context_chars=10, max_tool_result_chars=256),
            FakeTools(),
            client=FakeClient([first, completion("report")]),
        ).run("Inspect")

        self.assertTrue(result.budget_exhausted)
        self.assertEqual(result.context_chars, 10)
        self.assertEqual(
            json.loads(result.trace[0].result)["error"]["code"],
            "context_budget",
        )

    def test_context_exhaustion_skips_remaining_tool_execution(self) -> None:
        first = completion(
            None,
            tool_calls=[
                tool_call("one", "read_file", '{"path":"README.md"}'),
                tool_call("two", "read_file", '{"path":"README_CN.md"}'),
                tool_call("three", "read_file", '{"path":"LICENSE"}'),
            ],
        )
        tools = FakeTools()
        result = RepoScoutAgent(
            settings(max_rounds=4, max_context_chars=10, max_tool_calls=5),
            tools,
            client=FakeClient([first, completion("incomplete report")]),
        ).run("Inspect")

        self.assertEqual(len(tools.calls), 1)
        self.assertEqual(len(result.trace), 3)
        self.assertTrue(result.budget_exhausted)
        self.assertTrue(all(item.error for item in result.trace))

    def test_public_dict_omits_raw_messages_and_tool_results(self) -> None:
        result = RepoScoutAgent(
            settings(),
            FakeTools(),
            client=FakeClient([completion("report")]),
        ).run("Inspect")

        public = result.to_dict()

        self.assertNotIn("messages", public)
        self.assertNotIn("trace", public)

    def test_invalid_tool_arguments_become_a_tool_result(self) -> None:
        first = completion(
            None,
            tool_calls=[tool_call("bad", "read_file", "not-json")],
        )
        tools = FakeTools()
        client = FakeClient([first, completion("recovered")])

        result = RepoScoutAgent(settings(), tools, client=client).run("Inspect")

        self.assertEqual(result.content, "recovered")
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(tools.calls, [])
        self.assertIn("not valid JSON", result.trace[0].error or "")
        tool_message = client.completions.requests[1]["messages"][-1]
        self.assertEqual(tool_message["role"], "tool")
        self.assertIn("invalid_arguments", tool_message["content"])

    def test_invalid_report_gets_a_tool_free_repair_round(self) -> None:
        client = FakeClient(
            [
                completion("draft [README.md:L1]"),
                completion("repaired [README.md:L1-L1]"),
            ]
        )
        events: list[dict[str, Any]] = []

        def validate(content: str, _: tuple[Any, ...]) -> dict[str, Any]:
            if content.startswith("repaired"):
                return {"valid": True, "error": None}
            return {
                "valid": False,
                "error": {
                    "code": "malformed",
                    "citation": "[README.md:L1]",
                },
            }

        result = RepoScoutAgent(
            settings(max_rounds=3),
            FakeTools(),
            client=client,
            on_event=events.append,
            report_validator=validate,
        ).run("Inspect")

        self.assertEqual(result.content, "repaired [README.md:L1-L1]")
        self.assertEqual(result.rounds, 2)
        self.assertNotIn("tools", client.completions.requests[1])
        repair_prompt = client.completions.requests[1]["messages"][-1]["content"]
        self.assertIn("Local citation validation rejected", repair_prompt)
        self.assertIn("[README.md:L1]", repair_prompt)
        self.assertIn("report_repair", [event["type"] for event in events])

    def test_report_repair_is_attempted_only_once(self) -> None:
        client = FakeClient([completion("draft one"), completion("draft two")])
        events: list[dict[str, Any]] = []

        result = RepoScoutAgent(
            settings(max_rounds=5),
            FakeTools(),
            client=client,
            on_event=events.append,
            report_validator=lambda *_: {
                "valid": False,
                "error": {"code": "missing"},
            },
        ).run("Inspect")

        self.assertEqual(result.rounds, 2)
        self.assertEqual(len(client.completions.requests), 2)
        self.assertEqual(
            [event["type"] for event in events].count("report_repair"),
            1,
        )

    def test_unexpected_tool_errors_are_sanitized_before_model_request(self) -> None:
        first = completion(
            None,
            tool_calls=[tool_call("explode", "read_file", '{"path":"README.md"}')],
        )

        def explode(*_: Any) -> dict[str, Any]:
            raise RuntimeError("/Users/alice/private.py TOKEN=secret-value")

        tools = FakeTools()
        tools.execute = explode
        client = FakeClient([first, completion("recovered")])

        result = RepoScoutAgent(settings(), tools, client=client).run("Inspect")

        tool_message = client.completions.requests[1]["messages"][-1]["content"]
        self.assertIn("tool execution failed unexpectedly", tool_message)
        self.assertNotIn("/Users/alice", tool_message)
        self.assertNotIn("secret-value", tool_message)
        self.assertEqual(result.trace[0].error, "tool execution failed unexpectedly")

    def test_last_round_is_reserved_for_final_synthesis(self) -> None:
        first = completion(
            None,
            tool_calls=[tool_call("read", "read_file", '{"path":"README.md"}')],
            finish_reason="tool_calls",
        )
        client = FakeClient([first, completion("final report")])
        result = RepoScoutAgent(
            settings(max_rounds=3), FakeTools(), client=client
        ).run("Inspect")

        self.assertEqual(result.content, "final report")
        self.assertFalse(result.budget_exhausted)
        self.assertIn("tools", client.completions.requests[0])
        self.assertNotIn("tools", client.completions.requests[1])
        final_instruction = client.completions.requests[1]["messages"][-1]["content"]
        self.assertIn("final synthesis round", final_instruction)

    def test_final_tool_request_reports_actual_round_count(self) -> None:
        first = completion(
            None,
            tool_calls=[tool_call("read", "read_file", '{"path":"README.md"}')],
            finish_reason="tool_calls",
        )
        invalid_final = completion(
            "",
            tool_calls=[tool_call("again", "read_file", '{"path":"README.md"}')],
            finish_reason="tool_calls",
        )

        result = RepoScoutAgent(
            settings(max_rounds=3),
            FakeTools(),
            client=FakeClient([first, invalid_final]),
        ).run("Inspect")

        self.assertEqual(result.rounds, 2)
        self.assertEqual(result.finish_reason, "invalid_final_tool_request")
        self.assertTrue(result.budget_exhausted)


if __name__ == "__main__":
    unittest.main()
