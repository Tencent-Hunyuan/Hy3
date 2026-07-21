"""示例 03：时延对比（非流式 vs 流式）

对比两种模式：
- 非流式：发请求 → 等全部生成完 → 一次性返回
- 流式：发请求 → 收到第一个 token（TTFT）就开始显示 → 逐字输出

运行:
    python 03_latency_compare.py              # 默认 3 次正式 + 1 次热身
    python 03_latency_compare.py --runs 5 --warmup 2
"""

import argparse
import os
import statistics
import time

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=int(os.environ.get("HY3_TIMEOUT_SECONDS", "300")),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")
# 本地部署（vLLM / SGLang）：与其他示例保持一致，用 chat_template_kwargs 透传 reasoning_effort。
# 时延对比默认关闭思考（no_think），得到最干净的首字延迟 / 总耗时。
REASONING = {"chat_template_kwargs": {"reasoning_effort": "no_think"}}


def measure_non_stream(prompt: str) -> float:
    """非流式总耗时：从发请求到拿到完整响应。"""
    start = time.perf_counter()
    client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        extra_body=REASONING,
    )
    return time.perf_counter() - start


def measure_stream(prompt: str) -> tuple[float, float]:
    """流式：(TTFT, 总耗时)。"""
    start = time.perf_counter()
    ttft = None

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        stream=True,
        stream_options={"include_usage": True},
        extra_body=REASONING,
    )

    for chunk in stream:
        # usage 尾块：choices 为空，仅带 usage；流式只计时，可忽略
        if not chunk.choices:
            continue
        if ttft is None and chunk.choices[0].delta.content:
            ttft = time.perf_counter() - start   # 第一个内容 token 到达
        if chunk.choices[0].finish_reason:
            break

    total = time.perf_counter() - start
    return ttft or total, total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    args = parser.parse_args()

    prompt = "解释快速排序算法的工作原理，约 200 字。"

    # 热身（不计入统计，消除冷启动影响）
    print(f"热身 {args.warmup} 次...")
    for _ in range(args.warmup):
        try:
            measure_non_stream(prompt)
            measure_stream(prompt)
        except Exception as exc:
            print(f"  [热身警告] 预热失败（已忽略）: {type(exc).__name__}: {exc}")

    print(f"正式测量 {args.runs} 次...\n")
    ns_times, ttfts, st_totals = [], [], []
    for i in range(args.runs):
        try:
            ns = measure_non_stream(prompt)
            ttft, st = measure_stream(prompt)
        except Exception as exc:
            print(f"  Run {i+1}/{args.runs}: 失败 - {type(exc).__name__}: {exc}")
            continue
        ns_times.append(ns)
        ttfts.append(ttft)
        st_totals.append(st)
        print(f"  Run {i+1}/{args.runs}: 非流式={ns:.2f}s  流式TTFT={ttft:.2f}s  流式总计={st:.2f}s")

    def stats(label: str, vals: list[float]) -> None:
        if not vals:
            return
        p50 = statistics.median(vals)
        s = sorted(vals)
        p95 = s[int(len(s) * 0.95)] if len(s) > 1 else s[-1]
        print(f"  {label:>10s}: 平均={statistics.mean(vals):.2f}s  P50={p50:.2f}s  P95={p95:.2f}s")

    print("\n" + "=" * 40)
    stats("非流式总耗时", ns_times)
    stats("流式TTFT", ttfts)
    stats("流式总耗时", st_totals)
    if ns_times and st_totals:
        print(f"\n  流式感知加速比(以首字计): ~{statistics.mean(ns_times)/statistics.mean(ttfts):.1f}x")


if __name__ == "__main__":
    main()
