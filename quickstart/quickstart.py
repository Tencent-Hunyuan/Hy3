from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

response = client.chat.completions.create(   
    model="hy3",
    messages=[
        {"role": "user", "content": "你好，请简单介绍一下你自己。"},
    ],
    temperature=0.9,
)

print(response.choices[0].message.content)