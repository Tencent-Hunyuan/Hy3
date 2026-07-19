"""不启 stdio，直接测 list/read 与（可选）Hy3 调用。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 保证同目录可导入
sys.path.insert(0, str(Path(__file__).resolve().parent))

import server as srv


def main() -> None:
    root = Path(__file__).resolve().parent
    os.environ.setdefault("HY3_MCP_ROOT", str(root))

    print("== list_dir ==")
    print(srv.list_dir("."))
    print()

    print("== read_file sample.py ==")
    print(srv.read_file("sample.py")[:500])
    print()

    if not os.environ.get("HY3_API_KEY"):
        print("未设置 HY3_API_KEY，跳过 Hy3 调用")
        return

    code = Path(root / "sample.py").read_text(encoding="utf-8")
    print("== hy3_code_review ==")
    print(srv.hy3_code_review(code, focus="正确性与可读性")[:1500])
    print()
    print("== hy3_answer ==")
    print(srv.hy3_answer("fib 的时间复杂度大概是多少？", context=code)[:800])


if __name__ == "__main__":
    main()
