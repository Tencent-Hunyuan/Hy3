"""
Hy3 API - 错误处理与重试示例 / Error Handling & Retry Example
包含基础错误捕获、指数退避重试、流式请求错误处理
"""

import time
from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIStatusError,
    BadRequestError,
    NotFoundError,
)

# ============================================================
# 配置 / Configuration
# ============================================================
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ============================================================
# 示例 1：基础错误捕获 / Basic Error Catching
# ============================================================
def basic_error_handling():
    """演示各种错误类型的捕获和处理"""
    print("=" * 60)
    print("基础错误处理 / Basic Error Handling")
    print("=" * 60)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            timeout=30.0,  # 30秒超时
        )
        print(f"\n成功：{response.choices[0].message.content}")

    except APIConnectionError as e:
        print(f"\n[连接错误] {e}")
        print("  排查：请检查服务是否已启动，端口是否正确。")
        print("  命令：curl http://127.0.0.1:8000/v1/models")

    except APITimeoutError as e:
        print(f"\n[超时错误] {e}")
        print("  排查：请求超时，请增加 timeout 参数或减少 max_tokens。")

    except RateLimitError as e:
        print(f"\n[限流错误] {e}")
        print("  排查：请求频率过高，请稍后重试或降低并发。")

    except BadRequestError as e:
        print(f"\n[请求错误] 400: {e.message}")
        print("  排查：请求参数格式有误，请检查 messages 结构。")

    except NotFoundError as e:
        print(f"\n[未找到] 404: {e.message}")
        print("  排查：模型名不匹配，请确认与 --served-model-name 一致。")

    except APIStatusError as e:
        print(f"\n[服务端错误] {e.status_code}: {e.message}")
        print("  排查：服务端内部错误，请稍后重试。")

    except Exception as e:
        print(f"\n[未知错误] {type(e).__name__}: {e}")


# ============================================================
# 示例 2：指数退避重试 / Exponential Backoff Retry
# ============================================================
def call_with_retry(
    messages: list,
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 60.0,
    **kwargs,
):
    """
    带指数退避的 API 调用

    参数:
        messages: 对话消息列表
        max_retries: 最大重试次数
        base_delay: 基础延迟秒数（每次翻倍）
        timeout: 单次请求超时时间
        **kwargs: 传递给 create() 的额外参数

    返回:
        API 响应对象

    异常:
        重试次数用尽后抛出原始异常
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                timeout=timeout,
                **kwargs,
            )
            if attempt > 0:
                print(f"  [尝试 {attempt + 1}/{max_retries + 1}] 成功！")
            return response

        except (APIConnectionError, APITimeoutError) as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  [尝试 {attempt + 1}/{max_retries + 1}] "
                      f"{type(e).__name__}，{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                print(f"  [尝试 {attempt + 1}/{max_retries + 1}] 重试次数用尽。")

        except RateLimitError as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  [尝试 {attempt + 1}/{max_retries + 1}] "
                      f"限流（429），{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                print(f"  [尝试 {attempt + 1}/{max_retries + 1}] 限流重试次数用尽。")

        except APIStatusError as e:
            last_error = e
            if e.status_code >= 500 and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  [尝试 {attempt + 1}/{max_retries + 1}] "
                      f"服务端错误（{e.status_code}），{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                # 4xx 错误不重试，直接抛出
                raise

        except (BadRequestError, NotFoundError):
            # 客户端错误不重试
            raise

    raise last_error


def demo_retry():
    """演示指数退避重试"""
    print("\n" + "=" * 60)
    print("指数退避重试 / Exponential Backoff Retry")
    print("=" * 60)

    try:
        response = call_with_retry(
            messages=[{"role": "user", "content": "你好！"}],
            max_retries=3,
            base_delay=1.0,
        )
        print(f"\n回复：{response.choices[0].message.content}")
    except Exception as e:
        print(f"\n最终失败：{type(e).__name__}: {e}")


# ============================================================
# 示例 3：流式请求的错误处理 / Streaming Error Handling
# ============================================================
def stream_with_retry(
    messages: list,
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 60.0,
):
    """
    带重试的流式请求

    注意：流式请求的错误可能在迭代过程中发生，
    需要在 for 循环外层捕获异常。
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True,
                timeout=timeout,
            )

            full_content = ""
            print("回复：", end="")

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    print(delta.content, end="", flush=True)
                    full_content += delta.content

            print()  # 换行
            return full_content

        except (APIConnectionError, APITimeoutError, RateLimitError) as e:
            last_error = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"\n  [重试 {attempt + 1}] {type(e).__name__}，{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                print(f"\n  [重试 {attempt + 1}] 重试次数用尽。")

        except APIStatusError as e:
            if e.status_code >= 500 and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"\n  [重试 {attempt + 1}] 服务端错误（{e.status_code}），{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                raise

    raise last_error


def demo_stream_retry():
    """演示流式请求的重试"""
    print("\n" + "=" * 60)
    print("流式请求重试 / Stream Retry")
    print("=" * 60)

    try:
        content = stream_with_retry(
            messages=[{"role": "user", "content": "用一句话介绍Python"}],
            max_retries=3,
        )
        print(f"\n总字符数：{len(content)}")
    except Exception as e:
        print(f"\n最终失败：{type(e).__name__}: {e}")


# ============================================================
# 示例 4：生产级封装 / Production-Ready Wrapper
# ============================================================
class Hy3Client:
    """生产级 Hy3 API 客户端，内置错误处理和重试"""

    def __init__(
        self,
        base_url: str = BASE_URL,
        api_key: str = API_KEY,
        model: str = MODEL,
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout: float = 60.0,
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout

    def chat(self, messages: list, stream: bool = False, **kwargs) -> str:
        """
        发送聊天请求并返回文本内容

        自动处理重试逻辑，区分可重试和不可重试错误。
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if stream:
                    return self._stream_chat(messages, **kwargs)
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        timeout=self.timeout,
                        **kwargs,
                    )
                    return response.choices[0].message.content

            except (APIConnectionError, APITimeoutError, RateLimitError) as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise RuntimeError(
                        f"请求失败（已重试 {self.max_retries} 次）：{e}"
                    ) from e

            except APIStatusError as e:
                if e.status_code >= 500 and attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise RuntimeError(f"API 错误 [{e.status_code}]: {e.message}") from e

            except (BadRequestError, NotFoundError) as e:
                raise RuntimeError(f"请求错误（不可重试）：{e}") from e

        raise RuntimeError(f"请求失败：{last_error}")

    def _stream_chat(self, messages: list, **kwargs) -> str:
        """流式聊天，收集完整内容"""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            timeout=self.timeout,
            **kwargs,
        )
        parts = []
        for chunk in stream:
            if chunk.choices[0].delta.content:
                parts.append(chunk.choices[0].delta.content)
        return "".join(parts)


def demo_production_client():
    """演示生产级客户端使用"""
    print("\n" + "=" * 60)
    print("生产级客户端 / Production Client")
    print("=" * 60)

    hy3 = Hy3Client(max_retries=3, timeout=60.0)

    try:
        result = hy3.chat(
            messages=[
                {"role": "system", "content": "你是一位专业的技术顾问。"},
                {"role": "user", "content": "什么是向量数据库？"},
            ],
        )
        print(f"\n回复：{result}")
    except RuntimeError as e:
        print(f"\n错误：{e}")


# ============================================================
# 运行示例
# ============================================================
if __name__ == "__main__":
    basic_error_handling()
    demo_retry()
    demo_stream_retry()
    demo_production_client()
