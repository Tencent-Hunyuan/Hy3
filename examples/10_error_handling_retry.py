"""Retry transient errors with exponential backoff and jitter."""

import os
import random
import time

from openai import (
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)


def main():
    # Disable SDK automatic retries so this example controls the policy.
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
        timeout=30.0,
        max_retries=0,
    )

    # Retry transient failures up to three total attempts.
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=[{"role": "user", "content": "你好，请简单介绍腾讯混元大模型。"}],
            )
            print(response.choices[0].message.content)
            return
        except (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError) as exc:
            if attempt == 3:
                raise
            # Exponential backoff plus random jitter avoids synchronized retries.
            delay = min(8.0, 2 ** (attempt - 1)) + random.uniform(0, 0.5)
            print(f"Attempt {attempt} failed: {type(exc).__name__}; retrying in {delay:.2f}s")
            time.sleep(delay)


if __name__ == "__main__":
    main()
