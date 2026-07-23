"""Hy3 API 示例公共工具"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置信息
BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")


def get_client():
    """创建 OpenAI 客户端"""
    return OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=60.0
    )


def print_response(title, response):
    """格式化打印响应"""
    message = response.choices[0].message
    print(f"\n{'='*50}")
    print(f"标题: {title}")
    print(f"{'='*50}")
    print(f"回复: {message.content}")
    print(f"结束原因: {response.choices[0].finish_reason}")
    print(f"Token 用量: {response.usage}")
    print(f"{'='*50}\n")