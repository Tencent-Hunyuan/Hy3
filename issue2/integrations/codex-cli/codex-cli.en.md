# Using Hy3 with Codex CLI

> 🌐 中文版本： [codex-cli.md](codex-cli.md)

## Introduction

[Codex CLI](https://github.com/openai/codex) is OpenAI's open-source terminal AI coding tool. It lets you generate, debug, and refactor code from the command line using natural language. Built on the OpenAI Agents SDK, it **supports connecting to any OpenAI-compatible API**, so you can configure Hy3 as the backend model.

## Use Cases

- A native terminal AI coding experience
- Automation script generation and batch file processing
- AI-driven steps in CI/CD pipelines
- A lightweight coding environment that doesn't need an IDE

## Requirements

| Item | Requirement |
|:---|:---|
| Node.js | ≥ 18 |
| Codex CLI | `npm install -g @openai/codex` |
| Hy3 service | Self-hosted OpenAI-compatible API endpoint |
| Terminal | macOS / Linux Terminal, or Windows PowerShell / WSL |

## Configuration

### Environment variable config

```bash
# Configure the Hy3 endpoint
export OPENAI_BASE_URL="https://tokenhub.tencentmaas.com/v1"
export OPENAI_API_KEY="your-api-key"
export CODEX_MODEL="hy3"

# Optional: set inference parameters
export CODEX_TEMPERATURE="0.9"
export CODEX_MAX_TOKENS="8192"
```

### Write to a config file (recommended)

Set the environment variable first, since codex does not allow using the env var directly:

setx HY3_API_KEY "your-api-key"

In `~/.codex/config.json` (or `.codex.yaml` in the project root):

```
model = "hy3"
model_provider = "hy3-tokenhub"

[model_providers.hy3-tokenhub]
name = "Tencent Hy3"
base_url = "https://tokenhub.tencentmaas.com/v1"
env_key = "HY3_API_KEY"
max_tokens = 262144
supports_tools = true
timeout = 180
```

## End-to-End Demos

### Demo 1: Generate an entire web page with one command

```bash
codex "Create a single-file HTML page: an elegant personal business card with avatar, name, title, and social links, using pure CSS animations"
```

**Hy3 output**:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Card</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        .card {
            background: rgba(255,255,255,0.95); border-radius: 20px;
            padding: 40px; text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: float 3s ease-in-out infinite;
            max-width: 360px; width: 90%;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        .avatar {
            width: 100px; height: 100px; border-radius: 50%;
            margin: 0 auto 20px; background: linear-gradient(135deg, #f093fb, #f5576c);
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 40px; font-weight: bold;
        }
        .name { font-size: 24px; font-weight: 700; color: #333; margin-bottom: 4px; }
        .title { color: #666; font-size: 14px; margin-bottom: 20px; }
        .bio { color: #555; font-size: 13px; line-height: 1.6; margin-bottom: 24px; }
        .links { display: flex; justify-content: center; gap: 16px; }
        .links a {
            display: inline-flex; align-items: center; justify-content: center;
            width: 40px; height: 40px; border-radius: 50%;
            background: #f0f0f0; color: #555; text-decoration: none;
            font-size: 18px; transition: all 0.3s ease;
        }
        .links a:hover { background: #667eea; color: white; transform: scale(1.1); }
    </style>
</head>
<body>
    <div class="card">
        <div class="avatar">J</div>
        <div class="name">John Doe</div>
        <div class="title">Full-Stack Engineer · Open-Source Enthusiast</div>
        <p class="bio">Passionate about technology, focused on web development and AI apps.<br>Active GitHub contributor and tech blogger.</p>
        <div class="links">
            <a href="#" title="GitHub">⌨</a>
            <a href="#" title="Twitter">𝕏</a>
            <a href="#" title="LinkedIn">in</a>
            <a href="#" title="Email">✉</a>
        </div>
    </div>
</body>
</html>
```

### Demo 2: Interactive refactoring

```bash
# Start Codex interactive mode
codex --model hy3

# In interactive mode:
> Read src/utils.py and convert the synchronous IO inside to an asyncio style
> Add type annotations and docstrings to the functions changed above
> Generate matching pytest test cases under tests/
```

### Demo 3: Batch file operations

```bash
codex "Read all .ts files under src/, find code that uses the any type, and replace each with an explicit type definition"
```

## Common Notes

| Issue | Cause | Solution |
|:---|:---|:---|
| `Error: Model not found` | Wrong model name in config | Use `hy3` (self-hosted) or `tencent/hy3` (OpenRouter) |
| Output truncated | `max_tokens` default too small | Change `maxTokens` in `~/.codex/config.json` |
| `reasoning_effort` has no effect | Codex CLI doesn't pass custom params by default | Pass it via `--extra-body` or modify the Codex source |
| Wrong path | Codex runs in the wrong directory | `cd` to the project root before running |
| Edit mode not working | File permission issue | Ensure the file is readable/writable; Codex has a confirmation step in interactive mode |


[← Back to Index](../README.en.md)
