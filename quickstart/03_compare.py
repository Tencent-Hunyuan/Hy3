"""示例 3: 流式 vs 非流式对比"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_client, MODEL

def test_non_streaming(client, prompt):
    """测试非流式请求"""
    print("   ⏳ 等待完整响应...")
    start = time.time()
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    
    elapsed = time.time() - start
    content = response.choices[0].message.content
    
    print(f"   ✅ 完成 ({elapsed:.2f}秒)")
    print(f"   📝 内容: {content[:60]}...")
    print(f"   📊 Token: {response.usage.total_tokens}")
    
    return elapsed, len(content)

def test_streaming(client, prompt):
    """测试流式请求"""
    print("   🌊 开始流式接收...")
    start = time.time()
    
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    
    first_token_time = None
    content = ""
    
    for chunk in stream:
        if first_token_time is None and chunk.choices[0].delta.content:
            first_token_time = time.time()
        if chunk.choices[0].delta.content:
            content += chunk.choices[0].delta.content
    
    elapsed = time.time() - start
    first_token_latency = first_token_time - start if first_token_time else 0
    
    print(f"   ✅ 完成 ({elapsed:.2f}秒)")
    print(f"   ⚡ 首 Token 时延: {first_token_latency:.2f}秒")
    print(f"   📝 内容: {content[:60]}...")
    print(f"   📊 长度: {len(content)} 字符")
    
    return elapsed, first_token_latency, len(content)

def main():
    print("\n⚖️  Hy3 流式 vs 非流式对比")
    print("="*50)
    
    client = get_client()
    prompt = "什么是微服务架构？请用 100 字左右概括其主要特点。"
    
    print(f"\n📌 测试 Prompt: {prompt}\n")
    
    print("🔹 非流式模式:")
    non_stream_time, non_stream_len = test_non_streaming(client, prompt)
    
    print("\n🔸 流式模式:")
    stream_time, first_token, stream_len = test_streaming(client, prompt)
    
    print("\n" + "="*50)
    print("📊 对比结果:")
    print("="*50)
    print(f"   非流式总耗时: {non_stream_time:.2f}秒")
    print(f"   流式总耗时: {stream_time:.2f}秒")
    print(f"   流式首 Token 时延: {first_token:.2f}秒")
    print(f"   内容长度: 非流式 {non_stream_len} 字符 | 流式 {stream_len} 字符")
    print("\n💡 结论:")
    print("   - 流式可以更快看到首 Token，提升用户体验")
    print("   - 非流式总耗时可能略短，但用户需等待完整响应")
    print("   - 实时交互场景推荐使用流式")

if __name__ == "__main__":
    main()