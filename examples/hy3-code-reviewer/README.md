# Hy3 Code Reviewer

AI-powered code review using Tencent Hy3 (295B MoE model).

## Quick Start

```bash
pip install openai
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_API_KEY=your-key
python review.py path/to/your/code.py
```

## Example

```bash
$ python review.py hello.py
🔍 Hy3 Code Review: hello.py

1. **Summary**: Simple Python script that prints "Hello World".
2. **Bugs**: No bugs found.
3. **Style**: Add a docstring and type hints for clarity.
4. **Security**: No security concerns.
5. **Improvements**: Consider using `if __name__ == "__main__"` guard.
```

## Requirements

- Python 3.10+
- `openai` package
- Hy3 API endpoint (vLLM/SGLang or Tencent cloud API)
