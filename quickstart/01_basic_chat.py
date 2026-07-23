"""示例 1: 基础聊天（单轮 + 多轮）"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_client, print_response, MODEL

def main():
    print("\n🚀 Hy3 基础聊天示例")
    print("="*50)
    
    client = get_client()
    
    # ============ 单轮对话 ============
    print("\n📌 1. 单轮对话")
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "用一句话总结什么是 RESTful API。"}
        ],
        temperature=0.7,
        top_p=1.0,
        max_tokens=200,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    
    print_response("单轮对话", response)
    
    # ============ 多轮对话 ============
    print("\n📌 2. 多轮对话")
    
    messages = [
        {"role": "system", "content": "你是一个 Python 编程助手。"},
        {"role": "user", "content": "Python 中如何读取 CSV 文件？"}
    ]
    
    print("\n🔄 第 1 轮:")
    response1 = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=300,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    print_response("多轮 - 第1轮", response1)
    
    messages.append({"role": "assistant", "content": response1.choices[0].message.content})
    messages.append({"role": "user", "content": "那如何把 CSV 数据存入 MySQL 数据库？"})
    
    print("\n🔄 第 2 轮:")
    response2 = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=500,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    print_response("多轮 - 第2轮", response2)

if __name__ == "__main__":
    main()