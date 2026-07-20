"""不启动 stdio，直接对 server 模块的 4 个 tool 做集成冒烟测试。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HY3_MCP_ROOT", str(ROOT))

import server as srv


def _check(desc: str, ok: bool) -> int:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {desc}")
    return 0 if ok else 1


def main() -> int:
    errors = 0

    # 1. load_dataset — CSV
    print("=" * 60)
    print("1. load_dataset CSV")
    csv_result = srv.load_dataset("sample_data.csv", max_rows=5)
    print(csv_result[:800])
    errors += _check("CSV 包含列名", "product" in csv_result and "total_sales" in csv_result)
    errors += _check("CSV 包含统计", "mean" in csv_result.lower())
    errors += _check("CSV 包含行数", "总行数" in csv_result)
    print()

    # 2. load_dataset — JSON
    print("=" * 60)
    print("2. load_dataset JSON")
    json_result = srv.load_dataset("sample_data.json", max_rows=5)
    print(json_result[:800])
    errors += _check("JSON 包含字段", "user_id" in json_result and "score" in json_result)
    errors += _check("JSON 检测空值", "空值" in json_result)
    print()

    # 3. load_dataset — 越界拒绝
    print("=" * 60)
    print("3. load_dataset 越界拒绝")
    escape_result = srv.load_dataset("../.env")
    errors += _check("越界被拒绝", "[错误]" in escape_result)
    print(escape_result[:200])
    print()

    # 4. load_dataset — 不支持格式
    print("=" * 60)
    print("4. load_dataset 格式拒绝")
    format_result = srv.load_dataset("server.py")
    errors += _check("格式被拒绝", "[错误]" in format_result)
    print(format_result[:200])
    print()

    # 5. web_search — DDG 回退
    print("=" * 60)
    print("5. web_search (DDG)")
    search_result = srv.web_search("data visualization best practices", max_results=2)
    print(search_result[:600])
    errors += _check("搜索返回结果", "搜索源:" in search_result and "URL:" in search_result)
    print()

    # 6. Hy3 测试（需 API Key）
    if not os.environ.get("HY3_API_KEY"):
        print("未设置 HY3_API_KEY，跳过 Hy3 工具测试")
    else:
        # 6a. hy3_analyze
        print("=" * 60)
        print("6a. hy3_analyze")
        analyze_result = srv.hy3_analyze(
            "sample_data.csv",
            "分析哪个产品的销售额最高，各区域表现如何",
            include_web=False,
        )
        print(analyze_result[:1200])
        errors += _check("分析有内容", len(analyze_result) > 50 and not analyze_result.startswith("[错误]") and not analyze_result.startswith("[Hy3 API"))
        print()

        # 6b. hy3_chart_guide
        print("=" * 60)
        print("6b. hy3_chart_guide")
        chart_result = srv.hy3_chart_guide(
            "sample_data.csv",
            "用柱状图对比各产品类别的总销售额",
        )
        print(chart_result[:1200])
        errors += _check("图表建议有代码", "import" in chart_result.lower() or "plt." in chart_result.lower())
        print()

    print("=" * 60)
    if errors == 0:
        print(f"PASS: 全部冒烟测试通过")
        return 0
    else:
        print(f"FAIL: {errors} 项测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
