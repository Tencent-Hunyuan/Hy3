"""连通性测试 - 验证 Hy3 API 是否可用。

用法：PYTHONPATH=src python scripts/smoke_test.py
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from hy3_mcp_server.llm_client import LLMClient, describe_active_backend


def main() -> int:
    load_dotenv()
    print(f"当前后端: {describe_active_backend()}")
    client = LLMClient()
    reply = client.chat([{"role": "user", "content": "只回复两个字：连通"}])
    print(f"模型返回: {reply!r}")
    print("✅ 连通性测试通过")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"❌ 连通性测试失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
