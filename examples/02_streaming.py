"""
Example 2: Streaming 鈥?娴佸紡璇锋眰 + 閫?chunk 瑙ｆ瀽
================================================

鏈ず渚嬫紨绀?Hy3 API 鐨勬祦寮忚緭鍑鸿兘鍔涳細
  - 鍚敤 streaming 妯″紡
  - 閫?chunk 瑙ｆ瀽 delta 鍐呭
  - 鍖哄垎 reasoning_content 鍜屾櫘閫?content
  - 璁＄畻娴佸紡浼犺緭鐨勭粺璁′俊鎭?
杩愯鏂瑰紡锛?    export HY3_API_KEY="your-api-key"
    python 02_streaming.py
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

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# ============================================================
# 1. 鍩烘湰娴佸紡璇锋眰
# ============================================================

print_section("1. 鍩烘湰娴佸紡璇锋眰 (Basic Streaming)")

prompt = "璇风敤涓夊彞璇濅粙缁嶄汉宸ユ櫤鑳界殑鍙戝睍鍘嗗彶銆?

print("馃摛 璇锋眰:")
print(f"   model: {MODEL}")
print(f"   stream: True")
print(f"   prompt: \"{prompt}\"")
print()

print("馃摜 娴佸紡杈撳嚭 (瀹炴椂鎵撳嵃):")
print("-" * 40)

stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9,
    max_tokens=512,
    stream=True,
)

# 鏀堕泦瀹屾暣鍐呭
full_content = ""
chunk_count = 0
start_time = time.time()

for chunk in stream:
    chunk_count += 1
    delta = chunk.choices[0].delta

    if delta.content:
        full_content += delta.content
        print(delta.content, end="", flush=True)

end_time = time.time()

print("\n" + "-" * 40)
print()
print(f"馃搳 缁熻:")
print(f"   鎬?chunks: {chunk_count}")
print(f"   鎬昏€楁椂: {end_time - start_time:.2f}s")
print(f"   杈撳嚭瀛楃鏁? {len(full_content)}")


# ============================================================
# 2. 娴佸紡璇锋眰 鈥?杩涢樁锛氶€?chunk 瑙ｆ瀽鎵€鏈夊瓧娈?# ============================================================

print_section("2. 閫?Chunk 瑙ｆ瀽 (Per-Chunk Parsing)")

prompt = "璇锋瘮杈?Python 鍜?JavaScript 鐨勪富瑕佸尯鍒€?

print("馃摛 璇锋眰:")
print(f"   prompt: \"{prompt}\"")

print()
print("馃摜 閫?chunk 璇︽儏 (鍓?10 涓?chunks):")
print(f"   {'#':<5} {'delta_content':<30} {'finish_reason':<15}")
print(f"   {'-'*5} {'-'*30} {'-'*15}")

stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9,
    max_tokens=256,
    stream=True,
)

chunk_count = 0
full_text = ""

for chunk in stream:
    chunk_count += 1
    delta = chunk.choices[0].delta
    finish_reason = chunk.choices[0].finish_reason or "null"
    content = delta.content or ""

    full_text += content

    if chunk_count <= 10:
        # 鎴柇鏄剧ず浠ラ伩鍏嶈繃闀?        display = content[:25].replace("\n", "\\n") + ("..." if len(content) > 25 else "")
        print(f"   {chunk_count:<5} {display:<30} {finish_reason:<15}")

if chunk_count > 10:
    print(f"   ... (鐪佺暐 {chunk_count - 10} 涓?chunks)")

print()
print(f"馃搳 缁熻:")
print(f"   鎬?chunks: {chunk_count}")
print(f"   瀹屾暣杈撳嚭闀垮害: {len(full_text)} 瀛楃")

print()
print("馃挰 瀹屾暣杈撳嚭:")
print(full_text[:300] + ("..." if len(full_text) > 300 else ""))


# ============================================================
# 3. 娴佸紡璇锋眰 鈥?甯?reasoning (娣卞害鎬濊€冩椂鍙敤)
# ============================================================

print_section("3. 娴佸紡璇锋眰 鈥?鎹曡幏鎺ㄧ悊杩囩▼ (Reasoning Content)")

prompt = "璁＄畻 15 * 37 + 28 * 43 鐨勭粨鏋溿€傝涓€姝ヤ竴姝ョ畻銆?

print("馃摛 璇锋眰:")
print(f"   prompt: \"{prompt}\"")
print(f"   reasoning_effort: \"high\" (灏濊瘯鍚敤娣卞害鎬濊€?")
print()
print("馃摜 娴佸紡杈撳嚭 (鍖哄垎 reasoning 鍜?answer):")
print("-" * 40)

try:
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=512,
        stream=True,
        # 娉ㄦ剰: 涓嶅悓骞冲彴 reasoning_effort 浼犻€掓柟寮忎笉鍚?        # TokenHub: 鐩存帴浼?reasoning_effort="high"
        # 鑷儴缃? 閫氳繃 extra_body
        reasoning_effort="high",
    )

    reasoning_text = ""
    answer_text = ""

    for chunk in stream:
        delta = chunk.choices[0].delta

        # reasoning_content: 妯″瀷鐨勬€濊€冭繃绋?        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            reasoning_text += delta.reasoning_content
            print(f"[鎬濊€僝 {delta.reasoning_content}", end="", flush=True)

        # content: 妯″瀷鏈€缁堣緭鍑?        if delta.content:
            answer_text += delta.content
            print(delta.content, end="", flush=True)

    print("\n" + "-" * 40)
    print()
    if reasoning_text:
        print(f"馃搳 鎬濊€冭繃绋?({len(reasoning_text)} 瀛楃)")
        print(f"馃搳 鏈€缁堢瓟妗?({len(answer_text)} 瀛楃)")
    else:
        print("鈩癸笍  褰撳墠璇锋眰鏈Е鍙戞繁搴︽€濊€冿紙reasoning_content 涓虹┖锛夈€?)
        print("   杩欏彲鑳芥槸 API 骞冲彴鎴栨ā鍨嬬増鏈殑宸紓锛岃浠ュ疄闄呭钩鍙版枃妗ｄ负鍑嗐€?)

except Exception as e:
    print(f"\n鈿狅笍  閿欒: {e}")
    print("   鎻愮ず: 閮ㄥ垎骞冲彴鍙兘涓嶆敮鎸?reasoning_effort 椤跺眰鍙傛暟锛?)
    print("   璇峰弬鑰?quickstart.md 浜嗚В涓嶅悓骞冲彴鐨勪紶鍙傛柟寮忋€?)


print()
print("鉁?Example 2 瀹屾垚锛?)
