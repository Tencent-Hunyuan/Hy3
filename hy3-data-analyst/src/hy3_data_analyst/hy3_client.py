"""Hy3 API client wrapper (OpenAI-compatible interface)."""

from openai import OpenAI

from .config import get_hy3_api_key, get_hy3_base_url, get_hy3_model


def get_hy3_client() -> tuple[OpenAI, str]:
    """Return (OpenAI client instance, model name)."""
    api_key = get_hy3_api_key()
    base_url = get_hy3_base_url()
    model = get_hy3_model()
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def ask_hy3(prompt: str, max_tokens: int = 2048) -> str:
    """Send a question to Hy3 and return the answer.

    Raises RuntimeError if HY3_API_KEY is not configured or the API call fails.
    """
    client, model = get_hy3_client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个数据分析助手。基于用户提供的数据样本和问题，给出简洁、有洞察力的分析和建议。"
                        "You are a data analysis assistant. Based on the data sample and question, "
                        "provide concise, insightful analysis and suggestions."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(
            f"Hy3 API 调用失败 / API call failed: {str(e)}\n"
            f"Base URL: {get_hy3_base_url()}\n"
            f"Model: {get_hy3_model()}"
        ) from e
