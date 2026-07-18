"""
06 · error handling & retry —— 超时 / 限流 / 网络错误的重试与退避
演示: (a) 正常调用成功路径; (b) 故意制造错误(非法 model)看如何被捕获;
     (c) 带指数退避的重试封装 (应对超时/限流/网络抖动)。
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openai import OpenAI, APITimeoutError, RateLimitError, APIConnectionError, APIStatusError
from common import BASE_URL, API_KEY, MODEL

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30.0, max_retries=0)


def chat_with_retry(messages, max_attempts=4, backoff_base=0.5):
    """带指数退避的重试: 仅对 网络类/限流类 错误重试, 业务错误直接抛。"""
    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(model=MODEL, messages=messages)
        except (APITimeoutError, APIConnectionError) as e:
            print(f"  [尝试 {attempt}/{max_attempts}] 网络/超时: {type(e).__name__}")
        except RateLimitError as e:
            print(f"  [尝试 {attempt}/{max_attempts}] 限流: {type(e).__name__}")
        except APIStatusError as e:
            # 4xx 业务错误 (如非法参数) 不应重试
            print(f"  [业务错误, 不重试] {e.status_code}: {e}")
            raise
        if attempt < max_attempts:
            wait = backoff_base * (2 ** (attempt - 1))  # 0.5, 1, 2, ...
            print(f"     退避 {wait:.1f}s 后重试...")
            time.sleep(wait)
    raise RuntimeError(f"{max_attempts} 次重试后仍失败")


# (a) 正常成功路径
print("=== (a) 正常调用 (应成功) ===")
r = chat_with_retry([{"role": "user", "content": "回复 OK"}])
print("  成功:", r.choices[0].message.content)

# (b) 故意制造业务错误: 非法 model
print("\n=== (b) 业务错误 (非法 model, 应被捕获且不重试) ===")
try:
    client.chat.completions.create(model="not-a-real-model", messages=[{"role": "user", "content": "hi"}])
except APIStatusError as e:
    print(f"  捕获 {type(e).__name__}: status={e.status_code}")
    print(f"  响应体: {str(e)[:200]}")

# (c) 演示超时重试: 把 timeout 调到极小, 故意触发 APITimeoutError
print("\n=== (c) 超时重试演示 (timeout=0.001s 故意超时) ===")
slow = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=0.001, max_retries=0)
for attempt in range(1, 4):
    try:
        slow.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": "hi"}])
        print(f"  [尝试 {attempt}] 意外成功")
        break
    except (APITimeoutError, APIConnectionError) as e:
        print(f"  [尝试 {attempt}] {type(e).__name__} -> 退避 {0.5*(2**(attempt-1)):.1f}s")
        time.sleep(0.5 * (2 ** (attempt - 1)))
