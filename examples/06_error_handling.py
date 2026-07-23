"""
Example 6: Error Handling & Retry 鈥?瓒呮椂/闄愭祦/缃戠粶閿欒鐨勯噸璇曚笌閫€閬?=================================================================

鏈ず渚嬫紨绀?Hy3 API 璋冪敤鐨勫仴澹敊璇鐞嗭細
  - 甯歌閿欒绫诲瀷璇嗗埆涓庡垎绫?  - 鎸囨暟閫€閬块噸璇曠瓥鐣?  - 瓒呮椂澶勭悊
  - 闄愭祦 (429) 鐨勬櫤鑳界瓑寰?  - 鐢熶骇绾у埆鐨勯噸璇曡楗板櫒

杩愯鏂瑰紡锛?    export HY3_API_KEY="your-api-key"
    python 06_error_handling.py
"""

import os
import time
import random
import functools
from openai import (
    OpenAI,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIError,
    InternalServerError,
    BadRequestError,
    AuthenticationError,
)

# ============================================================
# 閰嶇疆
# ============================================================

API_KEY = os.environ.get("HY3_API_KEY", "your-api-key-here")
BASE_URL = os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
MODEL = "hy3"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30.0)


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# ============================================================
# 1. 閿欒绫诲瀷璇嗗埆
# ============================================================

print_section("1. 甯歌閿欒绫诲瀷")

ERROR_TABLE = """
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?閿欒绫诲瀷                  鈹?HTTP 鐮?  鈹?澶勭悊绛栫暐                           鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?AuthenticationError      鈹?401      鈹?妫€鏌?API Key锛屼笉閲嶈瘯                鈹?鈹?BadRequestError          鈹?400      鈹?妫€鏌ヨ姹傚弬鏁帮紝涓嶉噸璇?                鈹?鈹?RateLimitError           鈹?429      鈹?绛夊緟鍚庨噸璇曪紙鎸囨暟閫€閬匡級               鈹?鈹?InternalServerError      鈹?500      鈹?鎸囨暟閫€閬块噸璇?                       鈹?鈹?APITimeoutError          鈹?鈥?       鈹?鎸囨暟閫€閬块噸璇曪紝澧炲ぇ timeout           鈹?鈹?APIConnectionError       鈹?鈥?       鈹?鎸囨暟閫€閬块噸璇曪紝妫€鏌ョ綉缁?              鈹?鈹?APIError (鍏朵粬)          鈹?鍏朵粬      鈹?鏍规嵁鍏蜂綋鎯呭喌鍐冲畾                     鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?"""
print(ERROR_TABLE)


# ============================================================
# 2. 鐢熶骇绾ч噸璇曡楗板櫒
# ============================================================

print_section("2. 鐢熶骇绾ч噸璇曡楗板櫒 (Retry with Exponential Backoff)")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_errors: tuple = (
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        InternalServerError,
    ),
):
    """
    鎸囨暟閫€閬块噸璇曡楗板櫒銆?
    鍙傛暟:
        max_retries: 鏈€澶ч噸璇曟鏁?        base_delay: 鍩虹绛夊緟鏃堕棿锛堢锛?        max_delay: 鏈€澶х瓑寰呮椂闂达紙绉掞級
        backoff_factor: 閫€閬垮洜瀛?        jitter: 鏄惁娣诲姞闅忔満鎶栧姩
        retryable_errors: 鍙噸璇曠殑閿欒绫诲瀷
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_error = e

                    if attempt == max_retries:
                        print(f"   鉂?宸茶揪鏈€澶ч噸璇曟鏁?({max_retries})锛屾斁寮冦€?)
                        raise

                    # 璁＄畻寤惰繜
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)  # 50%-100% 鎶栧姩

                    error_type = type(e).__name__
                    print(f"   鈿狅笍  绗?{attempt + 1}/{max_retries} 娆￠噸璇?鈥?"
                          f"{error_type}: {str(e)[:80]} 鈥?"
                          f"绛夊緟 {delay:.1f}s...")
                    time.sleep(delay)

                except (AuthenticationError, BadRequestError) as e:
                    # 涓嶅彲閲嶈瘯鐨勯敊璇?                    print(f"   鉂?涓嶅彲閲嶈瘯閿欒: {type(e).__name__}: {e}")
                    raise

            # 鐞嗚涓婁笉浼氳蛋鍒拌繖閲?            raise last_error

        return wrapper
    return decorator


# ============================================================
# 3. 浣跨敤閲嶈瘯瑁呴グ鍣ㄥ彂璧疯姹?# ============================================================

print_section("3. 浣跨敤閲嶈瘯瑁呴グ鍣?鈥?姝ｅ父璇锋眰绀轰緥")

@retry_with_backoff(max_retries=3, base_delay=1.0)
def chat_with_retry(messages, **kwargs):
    """甯﹁嚜鍔ㄩ噸璇曠殑瀵硅瘽璇锋眰"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        **kwargs,
    )


try:
    response = chat_with_retry(
        messages=[{"role": "user", "content": "鐢ㄤ竴鍙ヨ瘽闂€欎笘鐣屻€?}],
        temperature=0.9,
        max_tokens=64,
    )
    print(f"鉁?璇锋眰鎴愬姛:")
    print(f"   {response.choices[0].message.content}")
except Exception as e:
    print(f"鉂?璇锋眰澶辫触: {type(e).__name__}: {e}")


# ============================================================
# 4. 妯℃嫙瓒呮椂澶勭悊
# ============================================================

print_section("4. 瓒呮椂澶勭悊")

# 鍒涘缓涓€涓甫鐭秴鏃剁殑瀹㈡埛绔潵婕旂ず瓒呮椂澶勭悊
short_timeout_client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=0.001,  # 鏋佺煭瓒呮椂锛屽嚑涔庡繀瀹氳Е鍙?)

print("馃摛 鍙戦€佽姹傦紙浣跨敤鏋佺煭瓒呮椂浠ヨЕ鍙戣秴鏃堕敊璇級...")

try:
    response = short_timeout_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "浣犲ソ"}],
        max_tokens=10,
    )
    print("鉁?璇锋眰鎴愬姛锛堣秴鏃舵湭瑙﹀彂锛?)
except APITimeoutError as e:
    print(f"鈴?瓒呮椂閿欒鎹曡幏: {type(e).__name__}")
    print(f"   閿欒淇℃伅: {e}")
    print()
    print(f"馃挕 瑙ｅ喅鏂规:")
    print(f"   1. 澧炲ぇ timeout 鍙傛暟: OpenAI(timeout=60.0)")
    print(f"   2. 鍑忓皬 max_tokens 浠ョ缉鐭敓鎴愭椂闂?)
    print(f"   3. 浣跨敤 streaming 妯″紡鑾峰彇澧為噺杈撳嚭")
except Exception as e:
    print(f"   鍏朵粬閿欒: {type(e).__name__}: {e}")


# ============================================================
# 5. 閿欒澶勭悊鏈€浣冲疄璺?# ============================================================

print_section("5. 鐢熶骇鐜鎺ㄨ崘妯″紡")

print("""
浠ヤ笅鏄竴涓敓浜х骇 API 璋冪敤鐨勬帹鑽愭ā鏉匡細

```python
import time
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError

client = OpenAI(
    api_key="your-key",
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=60.0,       # 璁剧疆鍚堢悊瓒呮椂
    max_retries=2,      # SDK 鍐呯疆閲嶈瘯锛堜粎瀵圭綉缁滈敊璇級
)

def safe_chat(messages, max_retries=3, **kwargs):
    \"\"\"甯﹀畬鏁撮敊璇鐞嗙殑鐢熶骇绾у璇濆嚱鏁癨"\"\"
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                **kwargs,
            )
            return response

        except RateLimitError as e:
            # 429 鈥?绛夊緟鍚庨噸璇?            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt + random.uniform(0, 1)
            print(f"闄愭祦锛岀瓑寰?{wait:.1f}s 鍚庨噸璇?..")
            time.sleep(wait)

        except (APITimeoutError, APIConnectionError) as e:
            # 缃戠粶/瓒呮椂 鈥?鎸囨暟閫€閬?            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"缃戠粶閿欒锛岀瓑寰?{wait}s 鍚庨噸璇?..")
            time.sleep(wait)

        except Exception as e:
            # 鏈煡閿欒 鈥?璁板綍骞舵姏鍑?            print(f"鏈煡閿欒: {type(e).__name__}: {e}")
            raise

    return None
```

娉ㄦ剰浜嬮」:
  1. 瀵逛簬 401/400 绛夊鎴风閿欒锛屼笉搴旈噸璇曪紙璇锋眰鏈韩鏈夐棶棰橈級
  2. 瀵逛簬 429/500/瓒呮椂锛屾寚鏁伴€€閬块噸璇曟槸鍚堢悊绛栫暐
  3. 鐢熶骇鐜搴旇褰曟瘡娆￠噸璇曠殑鍏冩暟鎹紙鏃堕棿鎴炽€侀敊璇被鍨嬨€佸欢杩熺瓑锛?  4. 鍙娇鐢?tenacity 搴擄紙pip install tenacity锛夎幏寰楁洿瀹屽杽鐨勯噸璇曠鐞?  5. 璁剧疆鍚堢悊鐨?max_retries 鍜?max_delay 閬垮厤闆穿鏁堝簲
""")

print()
print("鉁?Example 6 瀹屾垚锛?)
print()
print("=" * 60)
print("  馃帀 鎵€鏈?6 涓ず渚嬪凡瀹屾垚锛?)
print("  杩斿洖 quickstart.md 鏌ョ湅瀹屾暣鏂囨。銆?)
print("=" * 60)
