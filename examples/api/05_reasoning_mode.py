"""Compare Hy3 direct-answer and preserved-thinking modes on TokenHub."""

from __future__ import annotations

import time
from typing import Any

from common import create_client, get_extra_field, load_config, usage_dict


def call_reasoning_mode(
    client: Any,
    model: str,
    prompt: str,
    *,
    enabled: bool,
    effort: str = "high",
) -> dict[str, Any]:
    extra_body: dict[str, Any] = {
        "thinking": {"type": "enabled" if enabled else "disabled"}
    }
    if enabled:
        extra_body["reasoning_effort"] = effort

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        top_p=1.0,
        max_tokens=2048,
        extra_body=extra_body,
    )
    elapsed = time.perf_counter() - start
    choice = response.choices[0]
    return {
        "id": response.id,
        "model": response.model,
        "thinking": extra_body["thinking"]["type"],
        "reasoning_effort": effort if enabled else None,
        "reasoning_content": get_extra_field(choice.message, "reasoning_content"),
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "usage": usage_dict(response),
        "elapsed_seconds": elapsed,
    }


def print_result(result: dict[str, Any]) -> None:
    print("id:", result["id"], "model:", result["model"])
    print(
        f"thinking={result['thinking']}, reasoning_effort={result['reasoning_effort']}"
    )
    print("reasoning_content:", result["reasoning_content"] or "<not returned>")
    print("answer:", result["content"])
    print("finish_reason:", result["finish_reason"])
    print("usage:", result["usage"])
    print("elapsed:", f"{result['elapsed_seconds']:.3f}s")


def main() -> None:
    config = load_config()
    client = create_client(config, timeout=120.0)
    prompt = (
        "一个水池单开进水管 3 小时注满，单开出水管 5 小时排空。"
        "两个管同时打开，注满水池需要多久？请给出答案。"
    )

    print("=== Thinking disabled ===")
    direct = call_reasoning_mode(client, config.model, prompt, enabled=False)
    print_result(direct)

    print("\n=== Thinking enabled, effort=high ===")
    reasoning = call_reasoning_mode(
        client, config.model, prompt, enabled=True, effort="high"
    )
    print_result(reasoning)

    print(
        "\nComparison: enabled thinking may use more tokens and take longer; "
        "use it for tasks where additional reasoning is worth the latency and cost."
    )


if __name__ == "__main__":
    main()
