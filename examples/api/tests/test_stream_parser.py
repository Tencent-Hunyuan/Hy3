from __future__ import annotations

from types import SimpleNamespace

import pytest

from common import StreamInterruptedError, aggregate_stream


def ns(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def chunk(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    tool_calls: list[object] | None = None,
    finish_reason: str | None = None,
    choices: bool = True,
    usage: object | None = None,
) -> SimpleNamespace:
    if not choices:
        return ns(choices=[], usage=usage)
    delta = ns(
        content=content,
        reasoning_content=reasoning,
        tool_calls=tool_calls or [],
    )
    return ns(choices=[ns(delta=delta, finish_reason=finish_reason)], usage=usage)


def tool_fragment(
    *,
    index: int,
    call_id: str | None = None,
    name: str | None = None,
    arguments: str | None = None,
) -> SimpleNamespace:
    return ns(
        index=index,
        id=call_id,
        type="function" if call_id else None,
        function=ns(name=name, arguments=arguments),
    )


def test_aggregate_stream_handles_empty_choices_usage_tail_and_tool_fragments() -> None:
    usage = ns(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    result = aggregate_stream(
        [
            chunk(reasoning="think "),
            chunk(
                tool_calls=[
                    tool_fragment(
                        index=0,
                        call_id="call-1",
                        name="convert_temperature",
                        arguments='{"value":',
                    )
                ]
            ),
            chunk(tool_calls=[tool_fragment(index=0, arguments="68}")]),
            chunk(content="20°C", finish_reason="tool_calls"),
            chunk(choices=False, usage=usage),
        ]
    )

    assert result.reasoning_content == "think "
    assert result.content == "20°C"
    assert result.finish_reason == "tool_calls"
    assert result.complete is True
    assert result.usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }
    assert result.tool_calls[0].id == "call-1"
    assert result.tool_calls[0].name == "convert_temperature"
    assert result.tool_calls[0].arguments == '{"value":68}'


def test_callbacks_receive_only_non_empty_deltas() -> None:
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    aggregate_stream(
        [chunk(), chunk(reasoning="r"), chunk(content="c", finish_reason="stop")],
        on_content=content_parts.append,
        on_reasoning=reasoning_parts.append,
    )
    assert content_parts == ["c"]
    assert reasoning_parts == ["r"]


def test_interrupted_stream_exposes_partial_result() -> None:
    def broken_stream() -> object:
        yield chunk(content="partial")
        raise ConnectionError("connection reset")

    with pytest.raises(StreamInterruptedError) as raised:
        aggregate_stream(broken_stream())
    assert raised.value.partial.content == "partial"
    assert raised.value.partial.complete is False


def test_callback_errors_are_not_misreported_as_stream_interruptions() -> None:
    def fail_callback(_text: str) -> None:
        raise ValueError("consumer failed")

    with pytest.raises(ValueError, match="consumer failed"):
        aggregate_stream([chunk(content="value")], on_content=fail_callback)


def test_missing_finish_reason_is_not_marked_complete() -> None:
    result = aggregate_stream([chunk(content="partial")])
    assert result.content == "partial"
    assert result.complete is False
