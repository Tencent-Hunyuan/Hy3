"""示例 6: 错误处理与重试"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_client, MODEL

def call_with_retry(max_retries=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"⚠️ 第 {i+1} 次尝试失败: {type(e).__name__}")
                    if i == max_retries - 1:
                        raise
                    wait = 2 ** i
                    print(f"⏳ 等待 {wait} 秒后重试...")
                    time.sleep(wait)
            return None
        return wrapper
    return decorator

def main():
    print("\n🛡️  Hy3 错误处理示例")
    print("="*50)
    
    client = get_client()
    
    @call_with_retry(max_retries=3)
    def safe_call():
        return client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好，请简单介绍一下自己。"}],
            max_tokens=80,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
        )
    
    try:
        print("\n📌 正常调用（带重试保护）:")
        response = safe_call()
        print(f"✅ 成功! 回复: {response.choices[0].message.content[:60]}...")
    except Exception as e:
        print(f"❌ 最终失败: {e}")
    
    print("\n" + "="*50)
    print("💡 错误处理最佳实践:")
    print("""
    1. 使用 try-except 捕获异常
    2. 对限流/超时使用指数退避重试
    3. 设置合理的超时时间
    4. 记录错误日志便于调试
    5. 设置最大重试次数避免无限循环
    """)

if __name__ == "__main__":
    main()