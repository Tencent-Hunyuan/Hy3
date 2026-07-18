"""
05 · reasoning mode —— 思考过程 开/关 对比 (探测脚本)
注意: Hy3 的思考开关精确参数 (reasoning_effort 取值) 以本脚本真实输出为准。
不同 effort 下对比: 是否产生 reasoning_content、回答质量/耗时差异。
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import get_client, MODEL

client = get_client()
Q = ("一个房间里有 3 个开关, 控制隔壁房间的 3 盏灯。"
     "你只能进隔壁房间看一次, 怎么分辨每个开关对应哪盏灯?")

# reasoning_effort 是 Hy3 特有参数, 用 extra_body 透传 (OpenAI SDK 未声明该字段)
for effort in ["low", "high"]:
    print(f"\n{'='*20} reasoning_effort = {effort} {'='*20}")
    t0 = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": Q}],
            max_tokens=3000,
            extra_body={"reasoning_effort": effort},
        )
        elapsed = time.perf_counter() - t0
        m = r.choices[0].message
        reasoning = getattr(m, "reasoning_content", None)
        print(f"  耗时: {elapsed*1000:.0f} ms | usage: {r.usage}")
        print(f"  产生思考过程: {bool(reasoning)}")
        if reasoning:
            print(f"  思考片段(前150字): {reasoning[:150]}...")
        print(f"  回答(前200字): {(m.content or '')[:200]}...")
    except Exception as e:
        print(f"  ❌ 报错: {type(e).__name__}: {e}")
