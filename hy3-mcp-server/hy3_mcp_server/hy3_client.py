import os
from openai import OpenAI
from openai.types.chat import ChatCompletion


class Hy3Client:
    def __init__(self):
        api_key = os.environ.get("HY3_API_KEY")
        if not api_key:
            raise ValueError("HY3_API_KEY environment variable is required")
        base_url = os.environ.get(
            "HY3_BASE_URL",
            "https://tokenhub-intl.tencentmaas.com/v1",
        )
        self.model = os.environ.get("HY3_MODEL_NAME", "hy3")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(
        self,
        messages: list[dict],
        reasoning_effort: str = "no_think",
        temperature: float = 0.9,
        top_p: float = 1.0,
    ) -> str:
        response: ChatCompletion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            extra_body={
                "chat_template_kwargs": {
                    "reasoning_effort": reasoning_effort,
                }
            },
        )
        return response.choices[0].message.content or ""
