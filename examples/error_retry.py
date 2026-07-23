from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError, Timeout
import os
import time

client = OpenAI(
    base_url="https://hy3.example.com/v1",
    api_key=os.getenv("HY3_API_KEY", "你的API_KEY"),
    timeout=10  # 设置基础超时时间
)

# ========== 1. 基础异常捕获示例 ==========
def basic_error_handle():
    print("=== 基础异常捕获 ===")
    try:
        resp = client.chat.completions.create(
            model="hy3-base",
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=100
        )
        print("请求成功：", resp.choices[0].message.content[:30], "...")
    except APIConnectionError:
        print("错误：网络连接失败，请检查网络或接口地址")
    except RateLimitError:
        print("错误：触发限流，请稍后再试")
    except Timeout:
        print("错误：请求超时，请检查网络或增大timeout")
    except APIError as e:
        print(f"接口返回错误：{e}")
    except Exception as e:
        print(f"未知错误：{e}")
    print()

# ========== 2. 指数退避自动重试 ==========
def request_with_retry(messages, max_retries=3, base_delay=1):
    """带重试退避的请求函数"""
    for retry in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="hy3-base",
                messages=messages,
                max_tokens=200
            )
            return resp
        except (RateLimitError, APIConnectionError, Timeout) as e:
            if retry == max_retries - 1:
                raise e
            # 指数退避：第1次等1秒，第2次等2秒，第3次等4秒
            delay = base_delay * (2 ** retry)
            print(f"第 {retry+1} 次请求失败，{delay}秒后重试... 错误：{type(e).__name__}")
            time.sleep(delay)

def retry_demo():
    print("=== 自动重试示例 ===")
    messages = [{"role": "user", "content": "请介绍一下API重试机制的作用"}]
    try:
        resp = request_with_retry(messages, max_retries=3)
        print("最终请求成功：", resp.choices[0].message.content[:50], "...")
    except Exception as e:
        print(f"重试全部失败，最终错误：{e}")
    print()

if __name__ == "__main__":
    basic_error_handle()
    retry_demo()
    print("=== 常见错误说明 ===")
    print("401 Unauthorized：API Key无效，请检查密钥")
    print("429 Rate Limit：请求频率超限，建议增加重试间隔")
    print("400 Bad Request：参数格式错误，请检查请求字段")
    print("5xx 服务端错误：服务端异常，稍后重试即可")
