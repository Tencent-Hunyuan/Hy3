import os
import random
import time

from openai import APIConnectionError, APITimeoutError, RateLimitError, OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=30.0)


def chat_with_retry(max_retries=4):
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": "Give one sentence about robust API clients.",
                    }
                ],
                max_tokens=128,
            )
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            if attempt == max_retries:
                raise

            sleep_seconds = min(2 ** attempt, 16) + random.uniform(0, 0.5)
            print(f"{type(exc).__name__}: retrying in {sleep_seconds:.1f}s...")
            time.sleep(sleep_seconds)


def main() -> None:
    response = chat_with_retry()
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
