"""
Example 5: Reasoning Mode 鈥?鎬濊€冭繃绋?寮€/鍏?瀵规瘮
================================================

鏈ず渚嬫紨绀?Hy3 鐨勩€屽揩鎱㈡€濊€冭瀺鍚堛€嶈兘鍔涳細
  - 蹇€濊€?(no_think / low)锛氱洿鎺ヨ緭鍑虹瓟妗堬紝閫傚悎鏃ュ父瀵硅瘽
  - 鎱㈡€濊€?(high / medium)锛氬厛鎺ㄧ悊鍐嶅洖绛旓紝閫傚悎澶嶆潅浠诲姟
  - 瀵规瘮鍚屼竴闂鍦ㄤ笉鍚屾帹鐞嗘ā寮忎笅鐨勮緭鍑哄樊寮?  - 灞曠ず濡備綍鑾峰彇 reasoning_content锛堟€濊€冭繃绋嬶級

杩愯鏂瑰紡锛?    export HY3_API_KEY="your-api-key"
    python 05_reasoning_mode.py
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
# 娴嬭瘯闂闆?# ============================================================

# 绠€鍗曢棶棰?鈥?涓嶉渶瑕佹繁搴︽€濊€?SIMPLE_QUESTION = "璇风敤涓€鍙ヨ瘽浠嬬粛鑵捐鍏徃銆?

# 涓瓑闅惧害 鈥?闇€瑕佷竴瀹氭帹鐞?MEDIUM_QUESTION = "涓€涓暱鏂瑰舰鐨勯暱鏄鐨?2 鍊嶏紝鍛ㄩ暱鏄?36 鍘樼背銆傛眰杩欎釜闀挎柟褰㈢殑闈㈢Н銆?

# 鍥伴毦闂 鈥?闇€瑕佹繁搴︽帹鐞?HARD_QUESTION = "鐢层€佷箼銆佷笝涓変汉涓彧鏈変竴涓汉璇翠簡鐪熻瘽銆傜敳璇达細'涔欏湪璇磋皫'銆備箼璇达細'涓欏湪璇磋皫'銆備笝璇达細'鐢插拰涔欓兘鍦ㄨ璋?銆傝闂皝璇翠簡鐪熻瘽锛熻閫愭鎺ㄧ悊銆?


def run_comparison(question: str, label: str):
    """瀵规瘮涓嶅悓 reasoning_effort 妯″紡涓嬬殑杈撳嚭"""
    print(f"\n{'鈹€' * 56}")
    print(f"馃摑 闂 ({label}): {question[:60]}...")
    print(f"{'鈹€' * 56}")

    modes = [
        ("no_think", "蹇€濊€?鈥?鐩存帴鍥炵瓟"),
        ("high", "鎱㈡€濊€?鈥?娣卞害鎺ㄧ悊"),
    ]

    results = {}

    for effort, description in modes:
        print(f"\n馃敼 {description} (reasoning_effort='{effort}')")
        print(f"{'鈹€' * 40}")

        start_time = time.time()

        try:
            # 浣跨敤娴佸紡浠ュ垎鍒崟鑾?reasoning_content 鍜?content
            stream = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": question}],
                temperature=0.9,
                max_tokens=1024,
                stream=True,
                reasoning_effort=effort,
            )

            reasoning_text = ""
            answer_text = ""
            chunk_count = 0

            for chunk in stream:
                chunk_count += 1
                delta = chunk.choices[0].delta

                # 鎹曡幏鎺ㄧ悊杩囩▼
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_text += delta.reasoning_content

                # 鎹曡幏鏈€缁堝洖绛?                if delta.content:
                    answer_text += delta.content

            end_time = time.time()

            # 鎵撳嵃缁撴灉
            if reasoning_text:
                print(f"   馃 鎬濊€冭繃绋?({len(reasoning_text)} 瀛楃):")
                # 缂╄繘鏄剧ず鎬濊€冨唴瀹圭殑鍓?300 瀛楃
                for line in reasoning_text[:300].split("\n"):
                    print(f"      {line}")
                if len(reasoning_text) > 300:
                    print(f"      ... (鍏?{len(reasoning_text)} 瀛楃)")

            print(f"\n   馃挰 鏈€缁堝洖绛?({len(answer_text)} 瀛楃):")
            for line in answer_text[:400].split("\n"):
                print(f"      {line}")
            if len(answer_text) > 400:
                print(f"      ... (鍏?{len(answer_text)} 瀛楃)")

            print(f"\n   鈴憋笍  鎬昏€楁椂: {end_time - start_time:.2f}s | "
                  f"chunks: {chunk_count} | "
                  f"鎬濊€? {len(reasoning_text)}瀛楃 | "
                  f"鍥炵瓟: {len(answer_text)}瀛楃")

            results[effort] = {
                "reasoning_chars": len(reasoning_text),
                "answer_chars": len(answer_text),
                "time": end_time - start_time,
                "chunks": chunk_count,
            }

        except Exception as e:
            print(f"   鈿狅笍 閿欒: {e}")
            print(f"   鎻愮ず: 閮ㄥ垎骞冲彴鍙兘涓嶆敮鎸侀《灞?reasoning_effort 鍙傛暟銆?)
            print(f"   鑷儴缃?(vLLM) 璇烽€氳繃 extra_body={{'chat_template_kwargs': {{'reasoning_effort': '{effort}'}}}} 浼犻€掋€?)
            results[effort] = None

    # 瀵规瘮鎬荤粨
    if all(v is not None for v in results.values()):
        print(f"\n   馃搳 瀵规瘮鎬荤粨:")
        print(f"   {'妯″紡':<15} {'鎬濊€冨瓧绗?:>8} {'鍥炵瓟瀛楃':>8} {'鑰楁椂':>8}")
        for effort, desc in modes:
            r = results[effort]
            print(f"   {effort:<15} {r['reasoning_chars']:>8} {r['answer_chars']:>8} {r['time']:>7.2f}s")

        # 鍒嗘瀽宸紓
        no_think = results["no_think"]
        high = results["high"]
        if high["reasoning_chars"] > no_think["reasoning_chars"]:
            print(f"\n   馃挕 娣卞害鎬濊€冩ā寮忎骇鐢熶簡 {high['reasoning_chars'] - no_think['reasoning_chars']} "
                  f"瀛楃鐨勯澶栨帹鐞嗗唴瀹广€?)
            print(f"   娣卞害鎬濊€冩ā寮忚€楁椂绾︽槸蹇€濊€冪殑 {high['time'] / no_think['time']:.1f} 鍊嶏紝")
            print(f"   浣嗙瓟妗堣川閲忛€氬父鏇撮珮锛堝挨鍏舵槸澶嶆潅鎺ㄧ悊棰橈級銆?)

    return results


# ============================================================
# 1. 绠€鍗曢棶棰樺姣?# ============================================================

print_section("1. 绠€鍗曢棶棰?鈥?蹇€濊€?vs 鎱㈡€濊€?)
run_comparison(SIMPLE_QUESTION, "绠€鍗?)


# ============================================================
# 2. 鍥伴毦闂瀵规瘮
# ============================================================

print_section("2. 鍥伴毦闂 鈥?蹇€濊€?vs 鎱㈡€濊€冿紙閲嶇偣瀵规瘮锛?)
run_comparison(HARD_QUESTION, "鍥伴毦")


# ============================================================
# 3. 鎺ㄧ悊妯″紡浣跨敤寤鸿
# ============================================================

print_section("3. 浣跨敤寤鸿")

print("""
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鎺ㄧ悊妯″紡         鈹?閫傜敤鍦烘櫙              鈹?鐗圭偣                  鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?no_think / low  鈹?鏃ュ父瀵硅瘽銆佺畝鍗曢棶绛?    鈹?閫熷害蹇紝鎴愭湰浣?        鈹?鈹?                鈹?淇℃伅妫€绱€佺炕璇?        鈹?鐩存帴杩斿洖绛旀           鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?medium          鈹?涓€鑸垎鏋愩€佺患鍚?        鈹?閫傚害鎺ㄧ悊锛屽钩琛￠€熷害璐ㄩ噺  鈹?鈹?                鈹?涓瓑闅惧害浠诲姟           鈹?                      鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?high            鈹?鏁板璇佹槑銆佸鏉傜紪绋?    鈹?娣卞害鎬濈淮閾撅紝鎺ㄧ悊鏇村噯纭? 鈹?鈹?                鈹?閫昏緫鎺ㄧ悊銆佷唬鐮佽皟璇?    鈹?鑰楁椂杈冮暱锛屾垚鏈緝楂?     鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
馃挕 鏈€浣冲疄璺?
  - 瀵逛簬鏄庣‘绠€鍗曠殑浠诲姟锛屼娇鐢?"no_think" 鑺傜渷鎴愭湰鍜屽欢杩?  - 瀵逛簬闇€瑕佹帹鐞嗙殑浠诲姟锛屽厛鐢?"high" 灏濊瘯
  - 鍙互閫氳繃姣旇緝涓ゆ璋冪敤鐨勭粨鏋滄潵鍒ゆ柇鏄惁闇€瑕佹繁搴︽€濊€?  - reasoning_content 鍙敤浜庡睍绀烘ā鍨嬬殑鎺ㄧ悊杩囩▼锛屽寮哄彲瑙ｉ噴鎬?
鈿狅笍 鑷儴缃?(vLLM) 鐢ㄦ埛娉ㄦ剰:
   reasoning_effort 閫氳繃 extra_body 浼犻€?
   extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}

   SGLang 鐢ㄦ埛璇峰弬鑰冩渶鏂?SGLang cookbook銆?""")

print()
print("鉁?Example 5 瀹屾垚锛?)
