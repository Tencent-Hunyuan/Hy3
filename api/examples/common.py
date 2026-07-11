"""Shared client configuration and response formatting for the Hy3 examples."""

import os
from typing import Any

from openai import OpenAI


def create_client(*, max_retries: int = 2, timeout: float = 60.0) -> OpenAI:
    return OpenAI(
        base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
        api_key=os.getenv("HY3_API_KEY", "EMPTY"),
        max_retries=max_retries,
        timeout=timeout,
    )


def model_name() -> str:
    return os.getenv("HY3_MODEL", "hy3")


def print_response(response: Any) -> None:
    """Print every generally useful field from a non-streaming response."""
    choice = response.choices[0]
    message = choice.message
    print(f"id: {response.id}")
    print(f"model: {response.model}")
    print(f"role: {message.role}")
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning:
        print(f"reasoning_content: {reasoning}")
    print(f"content: {message.content}")
    if message.tool_calls:
        for call in message.tool_calls:
            print(
                "tool_call: "
                f"id={call.id}, name={call.function.name}, "
                f"arguments={call.function.arguments}"
            )
    print(f"finish_reason: {choice.finish_reason}")
    if response.usage:
        print(
            "usage: "
            f"prompt={response.usage.prompt_tokens}, "
            f"completion={response.usage.completion_tokens}, "
            f"total={response.usage.total_tokens}"
        )
