"""示例 5: 推理模式对比"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_client, MODEL

def test_mode(client, prompt, mode):
    print(f"\n🔍 推理模式: {mode}")
    print("-" * 30)
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=400,
        extra_body={"chat_template_kwargs": {"reasoning_effort": mode}}
    )
    
    msg = response.choices[0].message
    reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
    
    print(f"📊 Token 用量: {response.usage.total_tokens}")
    print(f"🧠 思考过程: {'有' if reasoning else '无（直接输出）'}")
    print(f"💬 回答预览: {msg.content[:80]}...")
    return response

def main():
    print("\n🧠 Hy3 推理模式对比")
    print("="*50)
    
    client = get_client()
    prompt = "一个班级有 40 个学生，男生比女生多 6 人，问男生和女生各有多少人？请一步步解释。"
    
    print(f"\n📌 测试问题: {prompt}\n")
    
    for mode in ["no_think", "low", "high"]:
        test_mode(client, prompt, mode)

if __name__ == "__main__":
    main()