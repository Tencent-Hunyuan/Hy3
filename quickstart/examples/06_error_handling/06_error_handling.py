from openai import OpenAI, RateLimitError, APIError, APIConnectionError, APITimeoutError, BadRequestError
from dotenv import load_dotenv
import os
import time
import math
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=30,
)

def timeout_example():
    print("=== 超时处理示例 ===")
    messages = [
        {"role": "user", "content": "请写一篇关于人工智能的长文，不少于500字。"},
    ]

    try:
        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            max_tokens=2000,
        )
        print("成功!")
        print("回答长度:", len(response.choices[0].message.content), "字符")
    except APITimeoutError:
        print("错误: 请求超时")
    except APIConnectionError:
        print("错误: 网络连接失败")
    except Exception as e:
        print(f"错误: {e}")

def exponential_backoff_example():
    print("\n=== 指数退避重试示例 ===")
    messages = [
        {"role": "user", "content": "你好"},
    ]

    def chat_with_retry(max_retries=5, initial_delay=1):
        for attempt in range(max_retries):
            try:
                print(f"尝试 {attempt + 1}/{max_retries}")
                response = client.chat.completions.create(
                    model="hy3",
                    messages=messages,
                )
                return response.choices[0].message.content
            
            except RateLimitError:
                delay = initial_delay * (2 ** attempt) + random.random()
                print(f"限流! 等待 {delay:.2f} 秒后重试...")
                time.sleep(delay)
            
            except APIError as e:
                if e.status_code in [500, 502, 503, 504]:
                    delay = initial_delay * (2 ** attempt) + random.random()
                    print(f"服务端错误 ({e.status_code})! 等待 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    raise
            
            except Exception as e:
                print(f"未知错误: {e}")
                raise
        
        raise Exception("超过最大重试次数")

    try:
        result = chat_with_retry()
        print("成功!")
        print("回答:", result)
    except Exception as e:
        print(f"最终失败: {e}")

def complete_error_handling():
    print("\n=== 完整错误处理示例 ===")

    def safe_chat_completion(messages, model="hy3", max_retries=5, initial_delay=1, **kwargs):
        for attempt in range(max_retries):
            try:
                logger.info(f"第 {attempt + 1} 次尝试")
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs,
                )
                logger.info(f"请求成功，Token 消耗: {response.usage.total_tokens}")
                return response
            
            except BadRequestError as e:
                logger.error(f"请求参数错误: {e}")
                raise
            
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + random.random()
                    logger.warning(f"限流 (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                    time.sleep(delay)
                else:
                    logger.error("超过最大重试次数，限流错误")
                    raise
            
            except APIConnectionError as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + random.random()
                    logger.warning(f"网络连接错误 (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                    time.sleep(delay)
                else:
                    logger.error("超过最大重试次数，网络连接错误")
                    raise
            
            except APITimeoutError as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + random.random()
                    logger.warning(f"请求超时 (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                    time.sleep(delay)
                else:
                    logger.error("超过最大重试次数，请求超时")
                    raise
            
            except APIError as e:
                if e.status_code in [500, 502, 503, 504]:
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt) + random.random()
                        logger.warning(f"服务端错误 {e.status_code} (第 {attempt + 1} 次)，等待 {delay:.2f} 秒")
                        time.sleep(delay)
                    else:
                        logger.error(f"超过最大重试次数，服务端错误 {e.status_code}")
                        raise
                else:
                    logger.error(f"API 错误 {e.status_code}: {e}")
                    raise
            
            except Exception as e:
                logger.error(f"未知错误: {e}")
                raise
        
        raise Exception("超过最大重试次数")

    messages = [
        {"role": "user", "content": "请介绍一下腾讯混元大模型。"},
    ]

    try:
        response = safe_chat_completion(messages)
        print("成功!")
        print("回答:", response.choices[0].message.content[:100], "...")
    except Exception as e:
        print(f"失败: {e}")

if __name__ == "__main__":
    timeout_example()
    exponential_backoff_example()
    complete_error_handling()