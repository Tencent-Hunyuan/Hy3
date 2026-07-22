"""
对应Issue要求：error handling & retry（超时/限流/网络错误的重试与退避）
实现：指数退避重试策略（重试间隔逐次翻倍）
覆盖错误：超时、速率限制（429）、网络连接错误
"""
import time
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError

client = OpenAI(
    api_key="YOUR-API-KEY",
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=10  # 设置10秒超时
)


def call_with_retry(max_retries=3, base_delay=1):
    """
    带重试机制的API调用
    :param max_retries: 最大重试次数
    :param base_delay: 初始重试延迟（秒）
    """
    for attempt in range(max_retries + 1):
        try:
            print(f"第{attempt + 1}次尝试调用API...")
            response = client.chat.completions.create(
                model="hy3-preview",
                messages=[{"role": "user", "content": "用Python写一个快速排序算法"}],
                temperature=0.7
            )
            print("调用成功！模型回复：")
            print(response.choices[0].message.content)
            return response

        except RateLimitError as e:
            # 速率限制错误：等待后重试
            delay = base_delay * (2 ** attempt)
            print(f"触发速率限制（429），{delay}秒后重试... 错误：{e}")

        except APITimeoutError as e:
            # 超时错误：重试
            delay = base_delay * (2 ** attempt)
            print(f"请求超时，{delay}秒后重试... 错误：{e}")

        except APIConnectionError as e:
            # 网络连接错误：重试
            delay = base_delay * (2 ** attempt)
            print(f"网络连接失败，{delay}秒后重试... 错误：{e}")

        except Exception as e:
            # 其他未知错误：直接抛出
            print(f"未知错误：{e}")
            raise

        # 最后一次尝试失败，不再重试
        if attempt == max_retries:
            print(f"达到最大重试次数（{max_retries}），调用失败")
            raise

        time.sleep(delay)


if __name__ == "__main__":
    print("=== 错误重试机制测试 ===")
    try:
        call_with_retry(max_retries=3, base_delay=1)
    except Exception as e:
        print(f"最终调用失败：{e}")