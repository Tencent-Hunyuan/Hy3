"""03 compare non-stream vs stream: TTFT and total latency."""
import os
import time
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")
PROMPT = "写一首四句的短诗，主题是开源。"


def non_stream():
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=200,
        temperature=0.9,
        stream=False,
    )
    total = time.perf_counter() - t0
    text = resp.choices[0].message.content or ""
    # 非流式无标准 TTFT；用总耗时近似「首包即全文」
    return {"mode": "non-stream", "ttft_s": total, "total_s": total, "chars": len(text), "preview": text[:80]}


def streaming():
    t0 = time.perf_counter()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=200,
        temperature=0.9,
        stream=True,
    )
    ttft = None
    full = []
    for chunk in stream:
        if not chunk.choices:
            continue
        piece = chunk.choices[0].delta.content or ""
        if piece and ttft is None:
            ttft = time.perf_counter() - t0
        if piece:
            full.append(piece)
    total = time.perf_counter() - t0
    text = "".join(full)
    return {
        "mode": "stream",
        "ttft_s": ttft,
        "total_s": total,
        "chars": len(text),
        "preview": text[:80],
    }


if __name__ == "__main__":
    a = non_stream()
    b = streaming()
    print("=== non-stream ===")
    print(a)
    print("=== stream ===")
    print(b)
    print("\n说明: non-stream 的 ttft_s 记为总耗时（首包即完整响应）；stream 的 ttft_s 为第一个 content chunk 到达时间。")
