import json
import os
from typing import Any

from openai import OpenAI


base_url = os.getenv(
    "HY3_BASE_URL",
    "http://127.0.0.1:8000/v1",
)

api_key = os.getenv(
    "HY3_API_KEY",
    "EMPTY",
)

model = os.getenv(
    "HY3_MODEL",
    "hy3",
)


client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)


def print_request(payload: dict[str, Any]) -> None:
    """Print the complete request payload."""

    print("\n--- Request ---")
    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )


def print_response(response: Any) -> None:
    """Print and parse the complete API response."""

    print("\n--- Raw response ---")
    print(response.model_dump_json(indent=2))

    choice = response.choices[0]

    print("\n--- Parsed response ---")
    print(f"Response ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Finish reason: {choice.finish_reason}")
    print(f"Role: {choice.message.role}")
    print(f"Content: {choice.message.content}")

    if response.usage is not None:
        print("\n--- Token usage ---")
        print(f"Prompt tokens: {response.usage.prompt_tokens}")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        print(f"Total tokens: {response.usage.total_tokens}")


def single_turn_chat() -> None:
    """Run a single-turn chat completion."""

    print("=== Single-turn chat ===")

    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Hello! Can you briefly introduce yourself?",
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print_request(request_payload)

    response = client.chat.completions.create(
        **request_payload
    )

    print_response(response)


def multi_turn_chat() -> None:
    """Run a multi-turn conversation by preserving message history."""

    print("\n\n=== Multi-turn chat ===")

    messages = [
        {
            "role": "user",
            "content": "My name is Ben. Please remember it.",
        }
    ]

    first_request = {
        "model": model,
        "messages": messages,
        "temperature": 0.9,
        "top_p": 1.0,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print("\n### First turn")
    print_request(first_request)

    first_response = client.chat.completions.create(
        **first_request
    )

    print_response(first_response)

    first_reply = first_response.choices[0].message.content

    if first_reply is None:
        raise ValueError("The first response did not contain text content.")

    # Preserve the assistant response in conversation history.
    messages.append(
        {
            "role": "assistant",
            "content": first_reply,
        }
    )

    # Add the next user turn.
    messages.append(
        {
            "role": "user",
            "content": "What is my name?",
        }
    )

    second_request = {
        "model": model,
        "messages": messages,
        "temperature": 0.9,
        "top_p": 1.0,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print("\n### Second turn")
    print_request(second_request)

    second_response = client.chat.completions.create(
        **second_request
    )

    print_response(second_response)


if __name__ == "__main__":
    single_turn_chat()
    multi_turn_chat()
