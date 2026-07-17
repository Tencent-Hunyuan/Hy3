from __future__ import annotations

from types import SimpleNamespace

import pytest

from common import (
    DuplicateToolCallError,
    ToolArgumentsError,
    ToolLoopError,
    ToolRoundLimitError,
    UnknownToolError,
    run_tool_loop,
)


def ns(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def tool_response(
    call_id: str,
    name: str,
    arguments: str,
    *,
    reasoning: str = "preserve exactly",
    content: str | None = None,
) -> SimpleNamespace:
    call = ns(id=call_id, type="function", function=ns(name=name, arguments=arguments))
    message = ns(
        role="assistant",
        content=content,
        reasoning_content=reasoning,
        tool_calls=[call],
    )
    return ns(choices=[ns(message=message, finish_reason="tool_calls")], model="hy3")


def final_response(content: str = "20°C") -> SimpleNamespace:
    message = ns(
        role="assistant",
        content=content,
        reasoning_content="final reasoning",
        tool_calls=None,
    )
    return ns(choices=[ns(message=message, finish_reason="stop")], model="hy3")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "convert_temperature",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "number"}},
                "required": ["value"],
                "additionalProperties": False,
            },
        },
    }
]


def test_tool_loop_preserves_reasoning_and_returns_tool_result() -> None:
    responses = iter(
        [
            tool_response("call-1", "convert_temperature", '{"value": 68}'),
            final_response(),
        ]
    )
    calls: list[list[dict[str, object]]] = []

    def create_completion(**kwargs: object) -> object:
        calls.append(list(kwargs["messages"]))  # type: ignore[arg-type]
        return next(responses)

    result = run_tool_loop(
        create_completion,
        messages=[{"role": "user", "content": "Convert 68 F"}],
        tools=TOOLS,
        handlers={
            "convert_temperature": lambda value: {"celsius": (value - 32) * 5 / 9}
        },
        request_kwargs={"model": "hy3"},
        max_tool_rounds=2,
    )

    assistant = calls[1][1]
    assert assistant["content"] is None
    assert assistant["reasoning_content"] == "preserve exactly"
    assert assistant["tool_calls"][0]["id"] == "call-1"  # type: ignore[index]
    assert calls[1][2] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": '{"celsius": 20.0}',
    }
    assert result.tool_rounds == 1
    assert result.messages[-1]["content"] == "20°C"


def test_empty_choices_are_rejected_before_response_callback() -> None:
    callbacks: list[int] = []

    with pytest.raises(ToolLoopError, match="no choices"):
        run_tool_loop(
            lambda **_kwargs: ns(choices=[]),
            messages=[{"role": "user", "content": "convert"}],
            tools=TOOLS,
            handlers={"convert_temperature": lambda value: value},
            request_kwargs={"model": "hy3"},
            on_response=lambda index, _response: callbacks.append(index),
        )

    assert callbacks == []


@pytest.mark.parametrize("arguments", ["not-json", "[]", '{"value": "hot"}', "{}"])
def test_bad_tool_arguments_are_rejected(arguments: str) -> None:
    with pytest.raises(ToolArgumentsError):
        run_tool_loop(
            lambda **_kwargs: tool_response("call-1", "convert_temperature", arguments),
            messages=[{"role": "user", "content": "convert"}],
            tools=TOOLS,
            handlers={"convert_temperature": lambda value: value},
            request_kwargs={"model": "hy3"},
        )


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(UnknownToolError):
        run_tool_loop(
            lambda **_kwargs: tool_response("call-1", "delete_everything", "{}"),
            messages=[{"role": "user", "content": "do it"}],
            tools=TOOLS,
            handlers={"convert_temperature": lambda value: value},
            request_kwargs={"model": "hy3"},
        )


def test_allowlisted_tool_failure_is_wrapped_without_result_details() -> None:
    def fail_tool(value: float) -> None:
        raise RuntimeError(f"sensitive handler detail: {value}")

    with pytest.raises(ToolLoopError, match="Allowlisted tool") as raised:
        run_tool_loop(
            lambda **_kwargs: tool_response(
                "call-1", "convert_temperature", '{"value":68}'
            ),
            messages=[{"role": "user", "content": "convert"}],
            tools=TOOLS,
            handlers={"convert_temperature": fail_tool},
            request_kwargs={"model": "hy3"},
        )
    assert "sensitive handler detail" not in str(raised.value)


def test_duplicate_tool_request_is_blocked() -> None:
    responses = iter(
        [
            tool_response("call-1", "convert_temperature", '{"value":68}'),
            tool_response("call-2", "convert_temperature", '{"value":68}'),
        ]
    )
    with pytest.raises(DuplicateToolCallError):
        run_tool_loop(
            lambda **_kwargs: next(responses),
            messages=[{"role": "user", "content": "convert"}],
            tools=TOOLS,
            handlers={"convert_temperature": lambda value: value},
            request_kwargs={"model": "hy3"},
            max_tool_rounds=3,
        )


def test_tool_round_limit_is_enforced() -> None:
    counter = 0

    def always_call(**_kwargs: object) -> object:
        nonlocal counter
        counter += 1
        return tool_response(
            f"call-{counter}", "convert_temperature", f'{{"value":{counter}}}'
        )

    with pytest.raises(ToolRoundLimitError):
        run_tool_loop(
            always_call,
            messages=[{"role": "user", "content": "convert forever"}],
            tools=TOOLS,
            handlers={"convert_temperature": lambda value: value},
            request_kwargs={"model": "hy3"},
            max_tool_rounds=2,
        )
    assert counter == 3
