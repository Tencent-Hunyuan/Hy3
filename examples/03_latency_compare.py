"""
Example 3: Non-Streaming vs Streaming 鈥?棣?Token 鏃跺欢 & 鎬昏€楁椂瀵规瘮
==================================================================

鏈ず渚嬪姣?Hy3 API 鐨勪袱绉嶈緭鍑烘ā寮忥細
  - 闈炴祦寮?(non-streaming)锛氱瓑寰呭畬鏁村搷搴斿悗涓€娆℃€ц繑鍥?  - 娴佸紡 (streaming)锛氶€愭杩斿洖鐢熸垚鍐呭

鍏抽敭鎸囨爣锛?  - TTFT (Time To First Token)锛氶涓?token 鐨勭瓑寰呮椂闂?  - 鎬昏€楁椂锛氫粠鍙戣捣璇锋眰鍒版敹鍒板畬鏁村洖澶嶇殑鏃堕棿
  - 鐢ㄦ埛浣撻獙宸紓锛氭祦寮忓彲鎻愬墠鐪嬪埌閮ㄥ垎鍐呭

杩愯鏂瑰紡锛?    export HY3_API_KEY="your-api-key"
    python 03_latency_compare.py
"""

import os
import time
from openai import OpenAI

# ============================================================
# 閰嶇疆
# ============================================================

API_KEY = os.environ.get("HY3_API_KEY", "your-api-key-here")
BASE_URL = os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
MODEL = "hy3"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=120.0)


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# ============================================================
# 娴嬭瘯閰嶇疆
# ============================================================

# 浣跨敤鐩稿悓 prompt 鍜屽弬鏁帮紝纭繚瀵规瘮鍏钩
PROMPTS = [
    "璇风敤 200 瀛楀乏鍙充粙缁嶆満鍣ㄥ涔犵殑涓昏鍒嗙被銆?,
    "璇峰垪鍑?Python 涓?10 涓父鐢ㄧ殑鏍囧噯搴撳苟绠€瑕佽鏄庡叾鐢ㄩ€斻€?,
    "璇峰啓涓€娈电害 150 瀛楃殑鏂囧瓧锛岃В閲婁粈涔堟槸娣卞害瀛︿範銆?,
]

# 闄愬埗杈撳嚭闀垮害浠ヤ繚鎸佹祴璇曞彲閲嶅
MAX_TOKENS = 300


# ============================================================
# 1. 闈炴祦寮忚姹?(Non-Streaming)
# ============================================================

print_section("1. 闈炴祦寮忚姹?(Non-Streaming)")

non_streaming_results = []

for i, prompt in enumerate(PROMPTS):
    print(f"馃摛 璇锋眰 #{i+1}: \"{prompt[:60]}...\"")

    start_time = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=MAX_TOKENS,
        stream=False,
    )
    end_time = time.time()

    total_time = end_time - start_time
    content = response.choices[0].message.content
    token_count = response.usage.completion_tokens

    non_streaming_results.append({
        "prompt": prompt,
        "total_time": total_time,
        "output_chars": len(content),
        "output_tokens": token_count,
    })

    print(f"   鉁?鎬昏€楁椂: {total_time:.2f}s | "
          f"杈撳嚭 tokens: {token_count} | "
          f"瀛楃鏁? {len(content)}")
    print()


# ============================================================
# 2. 娴佸紡璇锋眰 (Streaming)
# ============================================================

print_section("2. 娴佸紡璇锋眰 (Streaming)")

streaming_results = []

for i, prompt in enumerate(PROMPTS):
    print(f"馃摛 璇锋眰 #{i+1}: \"{prompt[:60]}...\"")

    ttft = None          # Time To First Token
    start_time = time.time()
    full_content = ""
    chunk_count = 0

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=MAX_TOKENS,
        stream=True,
        stream_options={"include_usage": True},  # 璇锋眰鍦ㄦ渶鍚?chunk 鍖呭惈 usage
    )

    for chunk in stream:
        chunk_count += 1
        delta = chunk.choices[0].delta

        if delta.content:
            # 璁板綍棣?token 鍒拌揪鏃堕棿
            if ttft is None:
                ttft = time.time() - start_time
            full_content += delta.content

    end_time = time.time()
    total_time = end_time - start_time

    streaming_results.append({
        "prompt": prompt,
        "ttft": ttft,
        "total_time": total_time,
        "chunk_count": chunk_count,
        "output_chars": len(full_content),
    })

    if ttft is not None:
        print(f"   鉁?TTFT: {ttft:.3f}s | "
              f"鎬昏€楁椂: {total_time:.2f}s | "
              f"chunks: {chunk_count} | "
              f"瀛楃鏁? {len(full_content)}")
    else:
        print(f"   鈿狅笍  鏈敹鍒版湁鏁堝唴瀹?)
    print()


# ============================================================
# 3. 瀵规瘮鍒嗘瀽
# ============================================================

print_section("3. 瀵规瘮鍒嗘瀽 (Comparison)")

print(f"{'鎸囨爣':<30} {'闈炴祦寮?:>12} {'娴佸紡':>12} {'宸紓':>12}")
print(f"{'-'*30} {'-'*12} {'-'*12} {'-'*12}")

for i in range(len(PROMPTS)):
    ns = non_streaming_results[i]
    ss = streaming_results[i]

    print(f"Prompt #{i+1}:")
    print(f"  {'鎬昏€楁椂':<28} {ns['total_time']:>11.2f}s {ss['total_time']:>11.2f}s "
          f"{ns['total_time'] - ss['total_time']:>+11.2f}s")

    if ss['ttft'] is not None:
        # 鐢ㄦ埛鎰熺煡寤惰繜锛氭祦寮忎负棣?token 鏃堕棿锛涢潪娴佸紡涓烘€昏€楁椂
        print(f"  {'鐢ㄦ埛鎰熺煡寤惰繜':<26} {ns['total_time']:>11.2f}s {ss['ttft']:>11.3f}s "
              f"{ns['total_time'] - ss['ttft']:>+11.2f}s 鈽?)
    print()

print("鈽?鐢ㄦ埛鎰熺煡寤惰繜 = 闈炴祦寮忕殑鎬昏€楁椂 vs 娴佸紡鐨勯 token 鏃堕棿")
print("   娴佸紡妯″紡涓嬶紝鐢ㄦ埛鍑犱箮绔嬪嵆鐪嬪埌鍝嶅簲寮€濮嬬敓鎴愶紝浣撻獙鏄捐憲鏇村ソ銆?)
print()

# 姹囨€荤粺璁?avg_ns_time = sum(r["total_time"] for r in non_streaming_results) / len(non_streaming_results)
avg_s_time = sum(r["total_time"] for r in streaming_results) / len(streaming_results)
avg_ttft = sum(r["ttft"] for r in streaming_results if r["ttft"]) / len(streaming_results)

print(f"馃搳 姹囨€荤粺璁?")
print(f"   闈炴祦寮忓钩鍧囨€昏€楁椂:     {avg_ns_time:.2f}s")
print(f"   娴佸紡骞冲潎鎬昏€楁椂:       {avg_s_time:.2f}s")
print(f"   娴佸紡骞冲潎棣?Token 寤惰繜: {avg_ttft:.3f}s")
print()
print(f"馃挕 缁撹:")
print(f"   - 娴佸紡妯″紡鐨勯 token 寤惰繜绾?{avg_ttft:.3f}s锛岀敤鎴峰彲蹇€熺湅鍒板搷搴?)
print(f"   - 闈炴祦寮忔ā寮忎笅鐢ㄦ埛闇€绛夊緟绾?{avg_ns_time:.2f}s 鎵嶈兘鐪嬪埌浠讳綍鍐呭")
print(f"   - 鎬昏€楁椂鏂归潰涓よ€呯浉杩戯紙宸窛涓昏鏉ヨ嚜缃戠粶浼犺緭妯″紡鐨勪笉鍚岋級")

print()
print("鉁?Example 3 瀹屾垚锛?)
