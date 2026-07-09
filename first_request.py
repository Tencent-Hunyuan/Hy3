import os
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=os.environ.get("TOKENHUB_API_KEY"),
)

response = client.chat.completions.create(
    model="hy3-preview",
    messages=[{"role": "user", "content": "请用一句话介绍你自己"}],
)

print(response.choices[0].message.content)
