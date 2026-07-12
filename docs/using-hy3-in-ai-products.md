# Using Hy3 in Popular AI Products

A step-by-step guide for integrating Hy3 (Tencent's 295B MoE model) with
popular AI tools and platforms.

## Supported Tools

| Tool | Type | Configuration | Guide |
|------|------|---------------|-------|
| Claude Code | CLI Agent | MCP Server | [Section 1](#1-claude-code) |
| CodeBuddy | IDE Agent | API Key | [Section 2](#2-codebuddy) |
| Cursor | IDE | API Key | [Section 3](#3-cursor) |
| Cline | VSCode Extension | API Key | [Section 4](#4-cline) |
| Open WebUI | Web Chat | OpenAI Compatible | [Section 5](#5-open-webui) |

## Quick Demo

Build a CLI chatbot using Hy3 in < 20 lines of Python:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

print("Hy3 Chat (type 'quit' to exit)")
messages = []
while True:
    user = input("\nYou: ")
    if user.lower() == "quit": break
    messages.append({"role": "user", "content": user})
    resp = client.chat.completions.create(
        model="hy3", messages=messages, max_tokens=1024
    )
    reply = resp.choices[0].message.content
    print(f"Hy3: {reply}")
    messages.append({"role": "assistant", "content": reply})
```

## 1. Claude Code

### Setup

1. Deploy Hy3 via vLLM or SGLang
2. Install the [Hy3 MCP Server](../examples/mcp-server/)
3. Configure Claude Code settings.json:

```json
{
  "mcpServers": {
    "hy3": {
      "command": "python",
      "args": ["/path/to/hy3/examples/mcp-server/server.py"],
      "env": {
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY"
      }
    }
  }
}
```

Now Claude Code has `hy3_chat`, `hy3_code`, and `hy3_analyze` tools.

## 2. CodeBuddy

### Setup

1. Open CodeBuddy settings
2. Add custom model provider:
   - Provider: OpenAI Compatible
   - Base URL: `http://<hy3-host>:8000/v1`
   - API Key: `EMPTY` (or your key)
   - Model: `hy3`

## 3. Cursor

### Setup

1. Settings → Models → Add Model
2. Configure:
   - Provider: OpenAI Compatible
   - Base URL: `http://<hy3-host>:8000/v1`
   - Model ID: `hy3`

## 4. Cline

### Setup

1. Cline settings → API Provider
2. Select "OpenAI Compatible"
3. Set Base URL: `http://<hy3-host>:8000/v1`
4. Set Model: `hy3`

## 5. Open WebUI

### Setup

1. Admin Panel → Settings → Connections
2. Add OpenAI API connection:
   - URL: `http://<hy3-host>:8000/v1`
   - Key: `EMPTY`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection refused | Ensure vLLM/SGLang is running: `curl http://127.0.0.1:8000/v1/models` |
| Model not found | Verify model path: `ls /path/to/Hy3/weights` |
| Slow response | Hy3 is a 295B model. Use quantization for faster inference |
| Out of memory | Reduce `max_tokens` or use tensor parallelism |
