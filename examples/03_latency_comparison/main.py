"""
对应Issue要求：non-streaming vs streaming（首token时延/总耗时对比）
统计指标：首token时延（TTFT）、总响应耗时、Token吞吐量
新增：输出模型实际回复内容
"""
import time
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",  
    base_url="https://tokenhub.tencentmaas.com/v1"
)

prompt = "详细解释Transformer模型的自注意力机制，字数200字以内，要求专业准确，同时通俗易懂，适合初学者理解。"

def test_non_streaming():
    """非流式请求：一次性返回全部内容"""
    print("=== 非流式请求测试 ===")
    start_time = time.time()
    response = client.chat.completions.create(
        model="hy3-preview",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        temperature=0.7,
        max_tokens=800
    )
    end_time = time.time()
    
    total_time = end_time - start_time
    content = response.choices[0].message.content
    token_count = response.usage.completion_tokens
    
  
    print(f"\n模型回复内容：\n{content}\n")
    print(f"总响应耗时：{total_time:.2f}秒")
    print(f"输出Token数：{token_count}")
    print(f"Token吞吐量：{token_count/total_time:.2f} tokens/秒\n")

def test_streaming_latency():
    """流式请求：统计首token时延 + 实时打印回复内容"""
    print("=== 流式请求测试（首token时延） ===")
    print("模型回复内容（实时输出）：\n", end="", flush=True)
    
    start_time = time.time()
    first_token_time = None
    full_content = ""  # 存储完整回复，方便后续使用
    token_count = 0
    
    stream = client.chat.completions.create(
        model="hy3-preview",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        temperature=0.7,
        max_tokens=800
    )
    
    for chunk in stream:
        # 关键修复：增加对 delta 和 content 的存在性检查，防止最后一个空chunk报错
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_content += content
            
            # 记录首token到达时间：只有真的收到有效内容才记录
            if first_token_time is None:
                first_token_time = time.time()
            token_count += 1
        
        if chunk.choices and chunk.choices[0].finish_reason == "stop":
            end_time = time.time()
            
            # 修正逻辑：只有收到有效内容才有TTFT，否则标记无数据
            if first_token_time is None:
                print("⚠️ 本次请求未输出有效内容，无首token时延数据")
                ttft = None
            else:
                ttft = first_token_time - start_time  # 首token时延
            total_time = end_time - start_time
            
            print(f"\n\n{'='*50}\n")
            # 仅当有TTFT数据时才打印
            if ttft is not None:
                print(f"首token时延（TTFT）：{ttft:.2f}秒")
            else:
                print(f"首token时延（TTFT）：无有效输出")
            print(f"总响应耗时：{total_time:.2f}秒")
            # 注意：这里的token_count是chunk计数，准确token数以usage为准
            print(f"近似输出Token数（按chunk计）：{token_count}")
            if hasattr(chunk, "usage") and chunk.usage:
                print(f"官方统计输出Token数：{chunk.usage.completion_tokens}")
                # 防止除零错误
                if total_time > 0:
                    print(f"官方统计Token吞吐量：{chunk.usage.completion_tokens/total_time:.2f} tokens/秒")

if __name__ == "__main__":
    test_non_streaming()
    test_streaming_latency()