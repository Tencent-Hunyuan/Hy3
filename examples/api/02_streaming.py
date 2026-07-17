"""Parse a Hy3 streaming response, including reasoning and usage-only chunks."""

from __future__ import annotations

import json
from dataclasses import asdict

from common import (
    ApiConfig,
    StreamInterruptedError,
    aggregate_stream,
    create_chat_completion,
    create_client,
    redact_data,
    run_example,
    thinking_body,
)


def main() -> None:
    config = ApiConfig.from_env()
    client = create_client(config)
    stream = create_chat_completion(
        client,
        model=config.model,
        messages=[{"role": "user", "content": "列出三个学习 Python 的建议。"}],
        temperature=0.3,
        max_tokens=512,
        stream=True,
        stream_options={"include_usage": True},
        extra_body=thinking_body(False),
    )

    try:
        result = aggregate_stream(
            stream,
            on_reasoning=lambda text: print(f"reasoning delta: {text!r}"),
            on_content=lambda text: print(f"content delta: {text!r}"),
        )
    except StreamInterruptedError as exc:
        partial = redact_data(asdict(exc.partial), secrets=[config.api_key])
        print("Stream interrupted; partial output is not a complete answer:")
        print(json.dumps(partial, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc

    print("\n=== Aggregated response ===")
    safe_result = redact_data(asdict(result), secrets=[config.api_key])
    print(json.dumps(safe_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_example(main)
