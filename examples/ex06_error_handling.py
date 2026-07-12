"""
ex06_error_handling.py
超时 / 限流 / 网络错误的重试与退避示例
"""

import os
import time
import random
from openai import OpenAI, APIError, RateLimitError, APITimeoutError


def create_client(timeout: float = 10.0):
    return OpenAI(
        api_key=os.environ.get("HY3_API_KEY"),
        base_url="https://tokenhub.tencentmaas.com/v1",
        timeout=timeout,
    )


def chat_with_retry(
    client: OpenAI,
    messages,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
):
    """带指数退避的重试封装"""
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                temperature=0.7,
                max_tokens=256,
            )
            return response
        except RateLimitError as e:
            print(f"[Attempt {attempt + 1}] Rate limit: {e}")
        except APITimeoutError as e:
            print(f"[Attempt {attempt + 1}] Timeout: {e}")
        except APIError as e:
            status = getattr(e, "status", None)
            if status is not None and 400 <= status < 500:
                print(f"[Attempt {attempt + 1}] Client error ({status}), no retry: {e}")
                raise
            print(f"[Attempt {attempt + 1}] API error: {e}")
        except Exception as e:
            print(f"[Attempt {attempt + 1}] Unexpected error: {e}")
            raise

        if attempt < max_retries:
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, 0.5)
            sleep_time = delay + jitter
            print(f"  -> 等待 {sleep_time:.2f}s 后重试...")
            time.sleep(sleep_time)
        else:
            print("  -> 已达到最大重试次数，放弃请求。")
            raise


def main():
    client = create_client(timeout=10.0)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用一句话总结重试机制的重要性。"},
    ]

    try:
        response = chat_with_retry(client, messages)
        print("\n最终回答:", response.choices[0].message.content)
    except Exception as e:
        print(f"\n请求最终失败: {e}")


if __name__ == "__main__":
    main()
