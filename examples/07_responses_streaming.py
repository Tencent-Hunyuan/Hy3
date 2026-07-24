"""Stream a Responses API response.

The current TokenHub response.created event may contain output: null,
which can cause high-level Responses stream parsers in some OpenAI SDK
versions to fail. This example parses SSE events directly instead.
"""

import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def iter_sse_events(response):
    """Convert an SSE response into (event_type, data) tuples."""
    event_type = "message"
    data_lines: list[str] = []

    # SSE records are separated by a blank line.
    for raw_line in response:
        line = raw_line.decode("utf-8").rstrip("\r\n")

        if not line:
            if data_lines:
                yield event_type, "\n".join(data_lines)
            event_type = "message"
            data_lines = []
        elif line.startswith("event:"):
            event_type = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").lstrip())

    if data_lines:
        yield event_type, "\n".join(data_lines)


def main():
    api_key = os.environ["HY3_API_KEY"]
    base_url = os.getenv(
        "HY3_BASE_URL",
        "https://tokenhub.tencentmaas.com/v1",
    ).rstrip("/")
    # Build the raw HTTP request because the SDK parser is not compatible
    # with the current TokenHub response.created output: null payload.
    request = Request(
        f"{base_url}/responses",
        data=json.dumps(
            {
                "model": "hy3",
                "input": "请用三句话介绍深圳。",
                "stream": True,
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )

    completed_response: dict[str, Any] | None = None

    try:
        with urlopen(request, timeout=60) as response:
            for event_type, raw_data in iter_sse_events(response):
                if raw_data == "[DONE]":
                    break

                event = json.loads(raw_data)
                event_name = event.get("type", event_type)

                # Handle text deltas and the terminal response event.
                if event_name == "response.output_text.delta":
                    print(event.get("delta", ""), end="", flush=True)
                elif event_name == "response.completed":
                    completed_response = event.get("response")
                elif event_name == "response.failed":
                    raise RuntimeError(json.dumps(event, ensure_ascii=False))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc

    if completed_response is not None:
        print(f"\n\nusage: {completed_response.get('usage')}")
    else:
        print("\n\nThe stream ended without a response.completed event.")


if __name__ == "__main__":
    main()
