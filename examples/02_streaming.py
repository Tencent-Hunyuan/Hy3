"""02 streaming: stream=True and parse chunks."""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")


def main():
    print("=== streaming ===")
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用三句话介绍人工智能，简短一些。"}],
        max_tokens=256,
        temperature=0.9,
        stream=True,
    )
    full = []
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        piece = delta.content or ""
        if piece:
            print(piece, end="", flush=True)
            full.append(piece)
    print("\n--- assembled ---")
    print("".join(full))


if __name__ == "__main__":
    main()
