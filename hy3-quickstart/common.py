"""
Hy3 客户端共享配置 —— 通过 OpenAI 兼容 SDK 调用腾讯混元 Hy3 (tokenhub)。
所有 example 脚本 import 本模块, 避免重复配置。
真实 Key 只从 .env / 环境变量读取, 绝不硬编码。
"""
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

# 让 examples/ 下的脚本能 import 到本模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()  # 读取同目录 .env

BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3")


def get_client(timeout: float = 60.0) -> OpenAI:
    """返回一个指向 Hy3 (tokenhub) 的 OpenAI 兼容客户端。"""
    if not API_KEY or API_KEY.startswith("your_"):
        raise SystemExit(
            "❌ 未配置 HY3_API_KEY。请 cp .env.example .env 并填入你的 tokenhub Key。"
        )
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=timeout)
