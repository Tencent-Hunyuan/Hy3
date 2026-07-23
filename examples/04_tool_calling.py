"""
Example 4: Tool Calling 鈥?鍗曟璋冪敤 + 澶氳疆宸ュ叿寰幆
===================================================

鏈ず渚嬫紨绀?Hy3 API 鐨勫伐鍏疯皟鐢?(Function Calling) 鑳藉姏锛?  - 瀹氫箟宸ュ叿 (Tool Schema)
  - 鍗曟宸ュ叿璋冪敤锛氭ā鍨嬭繑鍥?tool_calls
  - 澶氳疆宸ュ叿寰幆锛氭ā鍨?鈫?璋冪敤宸ュ叿 鈫?鍥炰紶缁撴灉 鈫?妯″瀷鏁村悎鍥炵瓟
  - tool_choice 鐨勭敤娉?(auto / none / required)

杩愯鏂瑰紡锛?    export HY3_API_KEY="your-api-key"
    python 04_tool_calling.py
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
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# ============================================================
# 瀹氫箟妯℃嫙宸ュ叿
# ============================================================

# 妯℃嫙鐨勫ぉ姘旀煡璇㈠嚱鏁?def get_weather(city: str) -> dict:
    """妯℃嫙澶╂皵鏌ヨ锛堝疄闄呴」鐩腑鍙浛鎹负鐪熷疄 API 璋冪敤锛?""
    weather_data = {
        "鍖椾含": {"temperature": "32掳C", "weather": "鏅?, "humidity": "45%"},
        "涓婃捣": {"temperature": "28掳C", "weather": "澶氫簯杞皬闆?, "humidity": "70%"},
        "娣卞湷": {"temperature": "33掳C", "weather": "闆烽樀闆?, "humidity": "85%"},
        "鏉窞": {"temperature": "30掳C", "weather": "闃?, "humidity": "60%"},
    }
    result = weather_data.get(city, {"temperature": "鏈煡", "weather": "鏃犳暟鎹?, "humidity": "鏈煡"})
    result["city"] = city
    return result


# 妯℃嫙鐨勫揩閫掓煡璇㈠嚱鏁?def query_express(tracking_number: str) -> dict:
    """妯℃嫙蹇€掓煡璇紙瀹為檯椤圭洰涓彲鏇挎崲涓虹湡瀹?API 璋冪敤锛?""
    return {
        "tracking_number": tracking_number,
        "status": "杩愯緭涓?,
        "location": "骞垮窞鍒嗘嫞涓績",
        "estimated_delivery": "2026-07-25",
        "carrier": "椤轰赴閫熻繍",
    }


# ============================================================
# 瀹氫箟宸ュ叿 Schema
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "鑾峰彇鎸囧畾鍩庡競鐨勫疄鏃跺ぉ姘斾俊鎭紝鍖呮嫭娓╁害銆佸ぉ姘旂姸鍐靛拰婀垮害",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "鍩庡競鍚嶇О锛屽锛氬寳浜€佷笂娴枫€佹繁鍦?,
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_express",
            "description": "鏍规嵁蹇€掑崟鍙锋煡璇㈠寘瑁圭殑鐗╂祦鐘舵€佸拰棰勮閫佽揪鏃堕棿",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "蹇€掑崟鍙?,
                    },
                },
                "required": ["tracking_number"],
            },
        },
    },
]

# 宸ュ叿鍚?鈫?瀹炵幇鍑芥暟鐨勬槧灏?TOOL_HANDLERS = {
    "get_weather": get_weather,
    "query_express": query_express,
}


# ============================================================
# 1. 鍗曟宸ュ叿璋冪敤
# ============================================================

print_section("1. 鍗曟宸ュ叿璋冪敤 (Single Tool Call)")

messages = [
    {"role": "user", "content": "鍖椾含浠婂ぉ澶╂皵鎬庝箞鏍凤紵"},
]

print("馃摛 璇锋眰:")
print(f"   model: {MODEL}")
print(f"   messages: [{{role: 'user', content: '鍖椾含浠婂ぉ澶╂皵鎬庝箞鏍凤紵'}}]")
print(f"   tools: [get_weather, query_express]")
print(f"   tool_choice: 'auto'")
print()

response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=TOOLS,
    tool_choice="auto",
    temperature=0.9,
)

assistant_msg = response.choices[0].message

print("馃摜 瀹屾暣 Response 瀵硅薄:")
print(f"   finish_reason: {response.choices[0].finish_reason}")
print(f"   has_tool_calls: {assistant_msg.tool_calls is not None}")

if assistant_msg.tool_calls:
    for i, tc in enumerate(assistant_msg.tool_calls):
        print(f"\n   Tool Call #{i+1}:")
        print(f"     id: {tc.id}")
        print(f"     function.name: {tc.function.name}")
        print(f"     function.arguments: {tc.function.arguments}")

        # 鎵ц宸ュ叿璋冪敤
        args = json.loads(tc.function.arguments)
        result = TOOL_HANDLERS[tc.function.name](**args)
        print(f"\n馃挰 妯℃嫙宸ュ叿鎵ц缁撴灉:")
        print(f"   {json.dumps(result, ensure_ascii=False)}")

        print(f"\n馃挰 绀轰緥杈撳嚭锛堝皢宸ュ叿缁撴灉杩斿洖妯″瀷鍚庯級:")
        # 鏋勫缓瀹屾暣鐨勫伐鍏疯皟鐢ㄦ秷鎭?        messages.append(assistant_msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False),
        })

        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
            max_tokens=256,
        )
        print(f"   {final_response.choices[0].message.content}")
else:
    print("   (妯″瀷閫夋嫨鐩存帴鍥炲锛屾湭瑙﹀彂宸ュ叿璋冪敤)")
    print(f"   content: {assistant_msg.content}")


# ============================================================
# 2. 澶氳疆宸ュ叿寰幆 (Multi-Turn Tool Loop)
# ============================================================

print_section("2. 澶氳疆宸ュ叿寰幆 (Multi-Turn Tool Loop)")

messages = [
    {
        "role": "user",
        "content": "璇峰府鎴戝仛涓変欢浜嬶細1) 鏌ヤ竴涓嬫繁鍦崇殑澶╂皵锛?) 鏌ュ揩閫掑崟鍙?SF1234567890 鐨勭墿娴佺姸鎬侊紱"
                   "3) 鏍规嵁澶╂皵鍜岀墿娴佹儏鍐碉紝缁欐垜涓€涓畝鐭殑鍑鸿寤鸿銆?,
    },
]

MAX_TOOL_ROUNDS = 5  # 闃叉鏃犻檺寰幆

print("馃摛 璇锋眰锛堝惈澶氫釜宸ュ叿闇€姹傦級:")
print(f"   user: {messages[0]['content'][:80]}...")
print()

for turn in range(MAX_TOOL_ROUNDS):
    print(f"--- 绗?{turn + 1} 杞?---")

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.9,
    )

    assistant_msg = response.choices[0].message

    # 濡傛灉妯″瀷涓嶅啀璋冪敤宸ュ叿锛岃緭鍑烘渶缁堝洖澶?    if not assistant_msg.tool_calls:
        print(f"鉁?妯″瀷鏈€缁堝洖澶?")
        print(f"   {assistant_msg.content}")
        break

    # 澶勭悊鎵€鏈夊伐鍏疯皟鐢?    messages.append(assistant_msg)
    for tc in assistant_msg.tool_calls:
        print(f"   馃敡 璋冪敤宸ュ叿: {tc.function.name}({tc.function.arguments})")
        args = json.loads(tc.function.arguments)
        result = TOOL_HANDLERS[tc.function.name](**args)
        print(f"   馃摝 宸ュ叿杩斿洖: {json.dumps(result, ensure_ascii=False)}")

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False),
        })
    print()

if turn + 1 >= MAX_TOOL_ROUNDS:
    print("鈿狅笍  杈惧埌鏈€澶у伐鍏疯疆娆￠檺鍒讹紝涓柇寰幆銆?)


# ============================================================
# 3. tool_choice 閫夐」璇存槑
# ============================================================

print_section("3. tool_choice 閫夐」瀵规瘮")

test_messages = [
    {"role": "user", "content": "浠婂ぉ蹇冩儏涓嶉敊锛岀粰鎴戞帹鑽愪竴閮ㄧ數褰卞惂銆?},
]

# 3a. tool_choice="none" 鈥?涓嶄娇鐢ㄥ伐鍏?print("3a. tool_choice='none' 鈥?涓嶄娇鐢ㄥ伐鍏凤紝鐩存帴鍥炲")
response = client.chat.completions.create(
    model=MODEL,
    messages=test_messages,
    tools=TOOLS,
    tool_choice="none",  # 妯″瀷涓嶈兘璋冪敤宸ュ叿
    temperature=0.9,
    max_tokens=128,
)
msg = response.choices[0].message
print(f"   has_tool_calls: {msg.tool_calls is not None}")
print(f"   content: {msg.content[:100]}...")
print()

# 3b. tool_choice="required" 鈥?寮哄埗璋冪敤宸ュ叿
print("3b. tool_choice='required' 鈥?寮哄埗璋冪敤宸ュ叿")
print("   (鍗充娇闂涓嶉渶瑕佸伐鍏凤紝妯″瀷涔熷繀椤昏皟鐢?")
response = client.chat.completions.create(
    model=MODEL,
    messages=test_messages,
    tools=TOOLS,
    tool_choice="required",
    temperature=0.9,
)
msg = response.choices[0].message
print(f"   has_tool_calls: {msg.tool_calls is not None}")
if msg.tool_calls:
    print(f"   浠嶇劧璋冪敤浜? {msg.tool_calls[0].function.name}")
print()

print("鉁?Example 4 瀹屾垚锛?)
