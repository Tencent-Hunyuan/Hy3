"""
Example 1: Basic Chat 鈥?鍗曡疆 & 澶氳疆瀵硅瘽
===========================================

鏈ず渚嬫紨绀?Hy3 API 鏈€鍩烘湰鐨勫璇濊兘鍔涳細
  - 鍗曡疆瀵硅瘽锛氬彂閫佷竴涓棶棰橈紝鑾峰彇鍥炲
  - 澶氳疆瀵硅瘽锛氬湪涓婁笅鏂囦腑杩涜澶氭浜や簰
  - System prompt锛氳瀹?AI 鐨勮鑹插拰琛屼负

杩愯鏂瑰紡锛?    export HY3_API_KEY="your-api-key"
    python 01_basic_chat.py
"""

import os
import json
from openai import OpenAI

# ============================================================
# 閰嶇疆
# ============================================================

API_KEY = os.environ.get("HY3_API_KEY", "your-api-key-here")
BASE_URL = os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
MODEL = "hy3"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def print_section(title: str):
    """鎵撳嵃鍒嗛殧鏍囬"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# ============================================================
# 1. 鍗曡疆瀵硅瘽 鈥?鏈€绠€璋冪敤
# ============================================================

print_section("1. 鍗曡疆瀵硅瘽 (Single-Turn Chat)")

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "浣犲ソ锛佽鐢ㄤ竴鍙ヨ瘽浠嬬粛浣犺嚜宸便€?},
    ],
    temperature=0.9,
    max_tokens=256,
)

print("馃摛 璇锋眰:")
print(f"   model: {MODEL}")
print(f"   messages: [{{role: 'user', content: '浣犲ソ锛佽鐢ㄤ竴鍙ヨ瘽浠嬬粛浣犺嚜宸便€?}}]")
print(f"   temperature: 0.9")
print(f"   max_tokens: 256")
print()

print("馃摜 瀹屾暣 Response 瀵硅薄:")
# 绠€鍖栨墦鍗?response 鐨勫叧閿瓧娈?print(f"   id: {response.id}")
print(f"   model: {response.model}")
print(f"   finish_reason: {response.choices[0].finish_reason}")
print(f"   content: {response.choices[0].message.content}")
print(f"   usage: prompt_tokens={response.usage.prompt_tokens}, "
      f"completion_tokens={response.usage.completion_tokens}, "
      f"total_tokens={response.usage.total_tokens}")

print()
print("馃挰 绀轰緥杈撳嚭:")
print(f"   {response.choices[0].message.content}")


# ============================================================
# 2. 澶氳疆瀵硅瘽 鈥?甯︿笂涓嬫枃
# ============================================================

print_section("2. 澶氳疆瀵硅瘽 (Multi-Turn Chat)")

messages = [
    {
        "role": "system",
        "content": "浣犳槸涓€涓笓涓氱殑 Python 缂栫▼鍔╂墜銆傝鐢ㄧ畝娲佹竻鏅扮殑涓枃鍥炵瓟闂锛?
                   "蹇呰鏃剁粰鍑轰唬鐮佺ず渚嬨€?,
    },
    {"role": "user", "content": "Python 涓浣曞弽杞竴涓垪琛紵"},
    {
        "role": "assistant",
        "content": "鏈変袱绉嶅父鐢ㄦ柟寮忥細\n"
                   "1. 浣跨敤 `.reverse()` 鏂规硶鍘熷湴鍙嶈浆锛歚my_list.reverse()`\n"
                   "2. 浣跨敤鍒囩墖鍒涘缓鏂板垪琛細`reversed_list = my_list[::-1]`\n\n"
                   "浣犳兂浜嗚В瀹冧滑鐨勫尯鍒悧锛?,
    },
    {"role": "user", "content": "鏄殑锛岃璇︾粏璇存槑杩欎袱绉嶆柟寮忕殑鍖哄埆銆?},
]

print("馃摛 璇锋眰 (澶氳疆娑堟伅):")
for i, msg in enumerate(messages):
    role = msg["role"]
    content_preview = msg["content"][:80].replace("\n", " ")
    print(f"   [{i}] {role}: {content_preview}...")
print()

response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.9,
    max_tokens=512,
)

print("馃摜 瀹屾暣 Response 瀵硅薄:")
print(f"   id: {response.id}")
print(f"   model: {response.model}")
print(f"   finish_reason: {response.choices[0].finish_reason}")
print(f"   usage: prompt_tokens={response.usage.prompt_tokens}, "
      f"completion_tokens={response.usage.completion_tokens}, "
      f"total_tokens={response.usage.total_tokens}")

print()
print("馃挰 绀轰緥杈撳嚭:")
print(f"   {response.choices[0].message.content}")


# ============================================================
# 3. 甯︾粨鏋勫寲杈撳嚭鐨勫崟杞璇?# ============================================================

print_section("3. 缁撴瀯鍖?JSON 杈撳嚭")

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "鍒楀嚭 3 绉嶅父瑙佺殑鎺掑簭绠楁硶锛岀敤 JSON 鏍煎紡杩斿洖锛?
                       "鍖呭惈 name锛堝悕绉帮級鍜?complexity锛堟椂闂村鏉傚害锛夊瓧娈点€?,
        },
    ],
    temperature=0.3,  # 杈冧綆娓╁害浠ュ寮烘牸寮忕‘瀹氭€?    max_tokens=512,
    response_format={"type": "json_object"},
)

print("馃摛 璇锋眰:")
print(f"   model: {MODEL}")
print(f"   response_format: {{type: 'json_object'}}")
print(f"   temperature: 0.3")
print()

print("馃摜 瀹屾暣 Response 瀵硅薄:")
print(f"   finish_reason: {response.choices[0].finish_reason}")
print(f"   content (raw JSON string):")
print(f"   {response.choices[0].message.content}")

# 灏濊瘯瑙ｆ瀽 JSON
try:
    parsed = json.loads(response.choices[0].message.content)
    print()
    print("馃挰 瑙ｆ瀽鍚庣殑绀轰緥杈撳嚭:")
    print(f"   {json.dumps(parsed, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print("   (JSON 瑙ｆ瀽澶辫触锛屾ā鍨嬭繑鍥炰簡闈炰弗鏍?JSON 鏍煎紡)")

print()
print("鉁?Example 1 瀹屾垚锛?)
