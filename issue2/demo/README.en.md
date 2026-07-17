# Hy3 Academic Writing Assistant Demo

> 🌐 中文版本： [README.md](README.md)

<p align="center">
  <img src="https://img.shields.io/badge/model-Hy3-667eea?style=for-the-badge" alt="Hy3">
  <img src="https://img.shields.io/badge/status-open--source-green?style=for-the-badge" alt="Open Source">
</p>

A web dual-tool application powered by **Tencent Hunyuan Hy3 (295B MoE)**, showcasing Hy3's capabilities in AI conversation and academic writing.

## Features

| Feature | Description | Hy3 Core Capability |
|:---|:---|:---|
| 💬 **AI Chat** | Streaming dialogue with a reasoning-mode toggle | Reasoning (`reasoning_effort`) |
| ✍️ **Paper Polish** | Three modes: academic polish / concise compress / CN-EN translation | Reasoning + long-text generation |

## Technical Highlights

- **Full streaming output**: real-time token stream via SSE (Server-Sent Events)
- **Reasoning toggle**: one-click `reasoning_effort=high` deep chain-of-thought
- **Multi-provider support**: self-hosted, OpenRouter, and custom presets
- **API connection test**: one-click Hy3 reachability check
- **Pure frontend**: HTML + CSS + JS, zero dependencies, open-and-run
- **Responsive design**: works on desktop and mobile

## Quick Start

**Prerequisite**: a reachable Hy3 OpenAI-compatible API endpoint (self-hosted vLLM/SGLang, OpenRouter, etc.).

```bash
# Option 1: open index.html directly in a browser

# Option 2: HTTP server (recommended, avoids CORS)
npx serve .
# or
python3 -m http.server 8080
```

After opening, fill in the **API Configuration** panel on the left:

| Field | Self-hosted | OpenRouter |
|:---|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` | `https://openrouter.ai/api/v1` |
| API Key | `EMPTY` | `sk-or-v1-your-key` |
| Model | `hy3` | `tencent/hy3` |

Click **Test Connection** to confirm.

## Usage

- **Chat mode**: select the "AI Chat" tab → (optional) enable "Deep Reasoning" → type a question → press Enter
- **Paper Polish**: select the "Paper Polish" tab → paste text → choose a mode → click "Start Polishing" → copy/download result

## File Structure

```
demo/
├── index.html    # Main page (full UI layout)
├── style.css     # Styles (gradient + animation + responsive)
├── script.js     # Logic (streaming API + background animation)
└── README.md     # This file
```

## References

- [Hy3 GitHub](https://github.com/Tencent-Hunyuan/Hy3)
- [Hy3 Integration Guide](../integrations/README.en.md)
