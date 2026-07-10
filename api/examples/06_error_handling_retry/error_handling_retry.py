"""
06 - Error Handling & Retry
演示超时、限流、网络错误的指数退避重试

Usage:
  export HY3_BASE_URL=http://127.0.0.1:8000/v1
  export HY3_API_KEY=EMPTY
  export HY3_MODEL=hy3
  python error_handling_retry.py
"""

import time
import random
from openai import OpenAI, APIError, APITimeoutError, RateLimitError
import os

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=30.0,
)


def chat_with_retry(messages, model=None, max_retries=3, base_delay=1.0):
    """
    带指数退避重试的 chat 调用

    Args:
        messages: 对话消息列表
        model: 模型名（默认使用环境变量）
        max_retries: 最大重试次数
        base_delay: 基础等待时间（秒）
    """
    model = model or MODEL
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.9,
                timeout=15.0,
            )
            return response

        except RateLimitError as e:
            print(f"[429] 限流 (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                print(f"  等待 {delay:.1f}s 后重试...")
                time.sleep(delay)
            last_error = e

        except APITimeoutError as e:
            print(f"[408] 超时 (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  等待 {delay:.1f}s 后重试...")
                time.sleep(delay)
            last_error = e

        except APIError as e:
            status = e.status_code if hasattr(e, 'status_code') else None
            if status and 500 <= status < 600:
                print(f"[{status}] 服务端错误 (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    print(f"  等待 {delay:.1f}s 后重试...")
                    time.sleep(delay)
                last_error = e
            else:
                raise

    raise last_error


def simulate_retry_scenarios():
    messages = [{"role": "user", "content": "用一句话介绍深圳。"}]

    # ===== 正常调用 =====
    print("=" * 50)
    print("正常调用")
    print("=" * 50)
    try:
        response = chat_with_retry(messages)
        print(f"回复: {response.choices[0].message.content}")
        print(f"Usage: {response.usage}\n")
    except Exception as e:
        print(f"失败: {e}\n")

    # ===== 故意超时测试（取消注释以运行） =====
    # print("=" * 50)
    # print("超时重试测试")
    # print("=" * 50)
    # try:
    #     response = chat_with_retry(
    #         messages, max_retries=2, base_delay=1.0
    #     )
    # except Exception as e:
    #     print(f"所有重试均失败: {e}")


if __name__ == "__main__":
    simulate_retry_scenarios()
