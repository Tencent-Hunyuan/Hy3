"""Hy3 API client wrapper using OpenAI-compatible interface."""

import os
import openai
from openai import OpenAI


def get_client() -> OpenAI:
    """Create an OpenAI client configured for Hy3 API."""
    api_key = os.environ.get("HY3_API_KEY")
    base_url = os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
    if not api_key:
        raise ValueError(
            "HY3_API_KEY environment variable is not set. "
            "Please set it in your .env file or environment."
        )
    return OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)


def get_model() -> str:
    """Get the Hy3 model name from environment."""
    return os.environ.get("HY3_MODEL", "hy3")


def chat(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    reasoning_effort: str = "no_think",
) -> str:
    """Send a chat completion request to Hy3 and return the response text.

    Args:
        messages: List of message dicts with role and content.
        temperature: Sampling temperature (0-2).
        max_tokens: Maximum tokens in the response.
        reasoning_effort: "no_think" for direct response, "low" or "high" for chain-of-thought.

    Returns:
        The assistant's response text.
    """
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=get_model(),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning_effort}},
        )
    except openai.AuthenticationError as e:
        raise ValueError(
            "Hy3 API authentication failed. Please check your HY3_API_KEY."
        ) from e
    except openai.RateLimitError as e:
        raise RuntimeError(
            "Hy3 API rate limit exceeded. Please wait a moment and try again."
        ) from e
    except openai.APITimeoutError as e:
        raise RuntimeError(
            "Hy3 API request timed out. The model may be under heavy load."
        ) from e
    except openai.APIConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Hy3 API at {os.environ.get('HY3_BASE_URL', 'default')}. "
            "Please check your network connection."
        ) from e

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("Hy3 API returned an empty response.")
    return content
