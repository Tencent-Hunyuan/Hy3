import os
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

# 创建一个客户端，所有的请求都通过client发送
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def single_turn():
    '''
    用户问一次问题，模型回答一次问题
    '''
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Give me three practical tips for writing reliable API clients."},
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )
    # 从返回结果中取出模型真正说的话并打印出来
    print(response.choices[0].message.content)

def multi_turn():
    '''
    模型先回答一个问题，然后用户基于上一次的回答继续进行追问
    message里面的两条消息：
    1. 第一条给模型设定身份和规则
    2. 第二条是用户的第一轮问题
    '''
    messages = [
        {"role": "system", "content": "You are a concise developer assistant."},
        {"role": "user", "content": "Explain what an API timeout is in one sentence."}
    ]
    # 第一次调用模型
    first = client.chat.completions.create(model=MODEL, messages=messages)
    answer = first.choices[0].message.content
    print("Assistant:", answer)

    # 把模型刚才的回答追加到messages里面
    messages.append({"role": "assistant", "content": answer})
    # 追加用户的新问题
    messages.append({"role": "user", "content": "Now give me one Python mitigation."})

    # 第二次调用模型
    second = client.chat.completions.create(model=MODEL, messages=messages)
    print("Assistant:", second.choices[0].message.content)

if __name__ == "__main__":
    print("=== Single Turn ===")
    single_turn()
    print("\n=== Multi Turn ===")
    multi_turn()
