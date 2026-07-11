import json
import os
import time
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


PROMPT = (
    "A company has 100 employees. "
    "60 know Python, 45 know Java, and 30 know SQL. "
    "25 know both Python and Java, "
    "20 know both Python and SQL, "
    "15 know both Java and SQL, "
    "and 10 know all three languages. "
    "How many employees know none of the three languages? "
    "Give the final answer and a concise explanation."
)


def print_json(
    title: str,
    data: Any,
) -> None:
    """Print JSON-compatible data."""

    print(f"\n=== {title} ===")

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )


def extract_reasoning_content(
    response: Any,
) -> str | None:
    """Extract reasoning_content when the endpoint returns it."""

    message_data = (
        response
        .choices[0]
        .message
        .model_dump()
    )

    reasoning_content = message_data.get(
        "reasoning_content"
    )

    if isinstance(reasoning_content, str):
        return reasoning_content

    return None


def extract_reasoning_tokens(
    response: Any,
) -> int | None:
    """Extract reasoning token usage when available."""

    if response.usage is None:
        return None

    details = response.usage.completion_tokens_details

    if details is None:
        return None

    return details.reasoning_tokens


def run_reasoning_mode(
    reasoning_effort: str,
) -> dict[str, Any]:
    """Run one request with the selected reasoning mode."""

    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "extra_body": {
            "reasoning_effort": reasoning_effort
        },
    }

    print_json(
        f"{reasoning_effort} request",
        request_payload,
    )

    start_time = time.perf_counter()

    response = client.chat.completions.create(
        **request_payload
    )

    end_time = time.perf_counter()

    latency = end_time - start_time

    print(
        f"\n=== {reasoning_effort} "
        "complete response ==="
    )
    print(response.model_dump_json(indent=2))

    message = response.choices[0].message
    reasoning_content = extract_reasoning_content(
        response
    )
    reasoning_tokens = extract_reasoning_tokens(
        response
    )

    prompt_tokens = None
    completion_tokens = None
    total_tokens = None

    if response.usage is not None:
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = (
            response.usage.completion_tokens
        )
        total_tokens = response.usage.total_tokens

    print(
        f"\n=== {reasoning_effort} "
        "parsed result ==="
    )
    print(f"Latency: {latency:.3f}s")
    print(
        "Finish reason:",
        response.choices[0].finish_reason,
    )
    print(f"Content: {message.content}")

    if reasoning_content is None:
        print("Reasoning content: not returned")
    else:
        print(
            "Reasoning content length:",
            len(reasoning_content),
        )

    print(
        "Reasoning tokens:",
        reasoning_tokens,
    )
    print(
        "Prompt tokens:",
        prompt_tokens,
    )
    print(
        "Completion tokens:",
        completion_tokens,
    )
    print(
        "Total tokens:",
        total_tokens,
    )

    return {
        "reasoning_effort": reasoning_effort,
        "latency": latency,
        "content": message.content,
        "reasoning_content": reasoning_content,
        "reasoning_tokens": reasoning_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def print_comparison(
    no_think_result: dict[str, Any],
    high_result: dict[str, Any],
) -> None:
    """Compare no_think and high reasoning modes."""

    print("\n\n=== Reasoning mode comparison ===")

    for result in [
        no_think_result,
        high_result,
    ]:
        mode = result["reasoning_effort"]

        print(f"\n{mode}:")
        print(
            f"Latency: "
            f"{result['latency']:.3f}s"
        )
        print(
            "Reasoning tokens:",
            result["reasoning_tokens"],
        )
        print(
            "Completion tokens:",
            result["completion_tokens"],
        )
        print(
            "Total tokens:",
            result["total_tokens"],
        )

        reasoning_content = result[
            "reasoning_content"
        ]

        if reasoning_content is None:
            print(
                "Reasoning content returned: no"
            )
        else:
            print(
                "Reasoning content returned: yes"
            )
            print(
                "Reasoning content length:",
                len(reasoning_content),
            )

        print(
            "Final answer:",
            result["content"],
        )

    print("\nNote:")
    print(
        "Reasoning effort can affect latency, "
        "token usage, and response behavior. "
        "A single run is not a benchmark."
    )


if __name__ == "__main__":
    no_think_result = run_reasoning_mode(
        "no_think"
    )

    high_result = run_reasoning_mode(
        "high"
    )

    print_comparison(
        no_think_result,
        high_result,
    )
