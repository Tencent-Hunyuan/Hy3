from openai import OpenAI, APIError, APITimeoutError, APIConnectionError, RateLimitError
import os
import time
import random
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("API_KEY", "EMPTY"),
    base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=5.0,
)


def retry_with_backoff(func, max_retries=3, base_delay=1.0, max_delay=10.0):
    def wrapper(*args, **kwargs):
        retries = 0
        delay = base_delay

        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except (APITimeoutError, APIConnectionError) as e:
                retries += 1
                if retries >= max_retries:
                    raise
                jitter = random.uniform(0, delay * 0.1)
                wait_time = delay + jitter
                print(f"  网络错误: {type(e).__name__} - 第 {retries}/{max_retries} 次重试，等待 {wait_time:.2f}s")
                time.sleep(wait_time)
                delay = min(delay * 2, max_delay)
            except RateLimitError as e:
                retries += 1
                if retries >= max_retries:
                    raise
                reset_after = getattr(e, 'reset_after', 1)
                wait_time = reset_after + random.uniform(0, 1)
                print(f"  限流错误: {type(e).__name__} - 第 {retries}/{max_retries} 次重试，等待 {wait_time:.2f}s")
                time.sleep(wait_time)
            except APIError as e:
                print(f"  API错误: {type(e).__name__} - {e}")
                raise

    return wrapper


@retry_with_backoff
def chat_with_retry(messages):
    return client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )


def error_handling_example():
    print("=== Error Handling & Retry 示例 ===")

    print("\n【完整请求参数】")
    print(f"  model: hy3")
    print(f"  messages: [{{'role': 'user', 'content': '你好'}}]")
    print(f"  timeout: 5.0")
    print(f"  retry策略: max_retries=3, base_delay=1.0s, max_delay=10.0s")

    print("\n【错误处理流程】")
    try:
        response = chat_with_retry([{"role": "user", "content": "你好"}])

        print("\n【成功响应解析】")
        print(f"  id: {response.id}")
        print(f"  model: {response.model}")
        print(f"  finish_reason: {response.choices[0].finish_reason}")
        print(f"  content: {response.choices[0].message.content}")

    except APITimeoutError as e:
        print(f"\n【超时错误】请求超时，已达到最大重试次数")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")

    except APIConnectionError as e:
        print(f"\n【网络错误】连接失败，已达到最大重试次数")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")

    except RateLimitError as e:
        print(f"\n【限流错误】请求被限流，已达到最大重试次数")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")

    except APIError as e:
        print(f"\n【API错误】服务端错误")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")


def timeout_test():
    print("\n\n=== 超时处理测试 ===")

    slow_client = OpenAI(
        api_key=os.getenv("API_KEY", "EMPTY"),
        base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000/v1"),
        timeout=1.0,
    )

    print("\n【请求参数】")
    print(f"  timeout: 1.0s (故意设置很短以触发超时)")

    try:
        response = slow_client.chat.completions.create(
            model="hy3",
            messages=[{"role": "user", "content": "请写一篇关于人工智能的长文"}],
            temperature=0.9,
            top_p=1.0,
        )
        print("\n【成功】响应正常返回")
    except APITimeoutError as e:
        print(f"\n【超时】请求在1秒内未完成")
        print(f"  错误: {type(e).__name__}")


def rate_limit_handling():
    print("\n\n=== 限流处理测试 ===")

    @retry_with_backoff
    def limited_request():
        return client.chat.completions.create(
            model="hy3",
            messages=[{"role": "user", "content": "测试"}],
        )

    print("\n【模拟高频请求】")
    for i in range(5):
        try:
            print(f"  请求 #{i+1}...")
            response = limited_request()
            print(f"    成功: {len(response.choices[0].message.content)} 字符")
        except Exception as e:
            print(f"    失败: {type(e).__name__}")
            break


if __name__ == "__main__":
    error_handling_example()
    timeout_test()
    rate_limit_handling()