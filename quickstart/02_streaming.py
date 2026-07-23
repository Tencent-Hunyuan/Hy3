"""示例 2: 流式请求（逐字输出）"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_client, MODEL

def main():
    print("\n🌊 Hy3 流式请求示例")
    print("="*50)
    
    client = get_client()
    
    print("\n📌 流式输出（逐字显示）:")
    print("-" * 30)
    
    start_time = time.time()
    
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "用一句话解释什么是 Docker，然后列举 3 个常用命令。"}
        ],
        temperature=0.7,
        max_tokens=200,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    
    full_response = ""
    chunk_count = 0
    first_chunk_time = None
    
    for chunk in stream:
        chunk_count += 1
        if first_chunk_time is None and chunk.choices[0].delta.content:
            first_chunk_time = time.time()
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    end_time = time.time()
    
    print(f"\n\n📊 统计信息:")
    print(f"   - 总块数: {chunk_count}")
    print(f"   - 首 Token 时延: {first_chunk_time - start_time:.2f} 秒")
    print(f"   - 总耗时: {end_time - start_time:.2f} 秒")
    print(f"   - 输出长度: {len(full_response)} 字符")

if __name__ == "__main__":
    main()