import os
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

prompt = "A train travels 120 km in 1.5 hours. What is its average speed?"

for effort in ["no_think", "high"]:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
    )
    print(f"\n=== reasoning_effort={effort} ===")
    print(response.choices[0].message.content)