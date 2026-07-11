"""Compare direct and reasoning-enabled Hy3 responses."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import create_client, model_name  # noqa: E402


def main() -> None:
    client = create_client()
    prompt = "若一个数除以 5 余 3，除以 7 余 4，求最小正整数。"

    for effort in ("no_think", "high"):
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=model_name(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
        )
        elapsed = time.perf_counter() - started
        message = response.choices[0].message
        print(f"=== reasoning_effort={effort} ===")
        print("id:", response.id)
        print("model:", response.model)
        print("role:", message.role)
        reasoning = getattr(message, "reasoning_content", None)
        print("reasoning_content:", reasoning or "<not returned>")
        print("content:", message.content)
        print("finish_reason:", response.choices[0].finish_reason)
        print(f"latency: {elapsed:.3f}s")
        if response.usage:
            print(
                "usage:",
                f"prompt={response.usage.prompt_tokens}, "
                f"completion={response.usage.completion_tokens}, "
                f"total={response.usage.total_tokens}",
            )
        print()


if __name__ == "__main__":
    main()
