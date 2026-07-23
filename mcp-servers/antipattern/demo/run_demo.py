"""AntiPattern MCP 一键演示脚本。

用法：
    python demo/run_demo.py

需要 .env 文件配置好 HY3_BASE_URL / HY3_API_KEY / HY3_MODEL。
依次调用 4 个 tool，展示 AntiPattern 的完整能力。
"""

import asyncio
import os
import sys
from pathlib import Path

# 确保能 import antipattern
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Windows 编码修复
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_env():
    """从项目根目录加载 .env 文件。"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        print(f"[ERROR] 未找到 .env 文件：{env_path}")
        print("请复制 .env.example 为 .env 并填入你的 API Key。")
        sys.exit(1)
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_result(result: str):
    # 截断过长输出（终端演示用）
    if len(result) > 2000:
        print(result[:2000])
        print(f"\n... [输出截断，完整长度 {len(result)} 字符]")
    else:
        print(result)


async def main():
    load_env()

    from antipattern.llm import Hy3Client, LLMError
    from antipattern.strategies import registry
    from antipattern.prompts import (
        build_challenge_prompt,
        build_remix_prompt,
        build_stress_prompt,
        build_escalate_prompt,
    )

    client = Hy3Client()
    print(f"[INFO] 连接 {client.model} @ {client.client.base_url}")
    print(f"[INFO] 策略库：{len(registry.all)} 条策略已加载")

    # --- Tool 1: challenge_design ---
    print_header("Tool 1: challenge_design（强度 4）")
    print("[输入] React + Redux + Ant Design 做后台管理系统，经典侧边栏导航 + 表格列表布局\n")

    strategies = registry.select("ui", intensity=4, count=2)
    print(f"[策略] {', '.join(s.name for s in strategies)}\n")

    system, user = build_challenge_prompt(strategies, 4, "React + Redux + Ant Design 做后台管理系统，经典侧边栏导航 + 表格列表布局")
    try:
        result1 = await client.reason(system, user, deep=True)
        print_result(result1)
    except LLMError as e:
        print(f"[ERROR] {e}")
        result1 = ""

    # --- Tool 2: remix_paradigm ---
    print_header("Tool 2: remix_paradigm（跨域嫁接）")
    print("[输入] 微服务间的通信架构设计\n")

    system, user = build_remix_prompt("微服务间的通信架构设计", "", 3)
    try:
        result2 = await client.reason(system, user, deep=True)
        print_result(result2)
    except LLMError as e:
        print(f"[ERROR] {e}")

    # --- Tool 3: stress_test_orthodoxy ---
    print_header("Tool 3: stress_test_orthodoxy（共识压力测试）")
    print("[输入] \"代码注释越多越好\"\n")

    system, user = build_stress_prompt("代码注释越多越好", "5人团队，Python 后端项目")
    try:
        result3 = await client.reason(system, user, deep=True)
        print_result(result3)
    except LLMError as e:
        print(f"[ERROR] {e}")

    # --- Tool 4: escalate ---
    if result1:
        print_header("Tool 4: escalate（加码到 5）")
        print("[输入] 上一轮 challenge_design 的输出\n")

        system, user = build_escalate_prompt(result1, 5, "更极端，从第一性原理彻底重建")
        try:
            result4 = await client.reason(system, user, deep=True)
            print_result(result4)
        except LLMError as e:
            print(f"[ERROR] {e}")

    print_header("Demo 完成")
    print("AntiPattern MCP Server 4 个 tool 全部演示完毕。")
    print("接入 MCP 客户端后，在对话中直接调用即可。")


if __name__ == "__main__":
    asyncio.run(main())
