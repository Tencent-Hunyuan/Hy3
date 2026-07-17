# Hy3 学术写作智能助手 Demo

> 🌐 English version: [README.en.md](README.en.md)

<p align="center">
  <img src="https://img.shields.io/badge/model-Hy3-667eea?style=for-the-badge" alt="Hy3">
  <img src="https://img.shields.io/badge/status-open--source-green?style=for-the-badge" alt="Open Source">
</p>

一个由**腾讯混元 Hy3（295B MoE）**驱动的 Web 双工具应用，展示 Hy3 在 AI 对话与学术写作场景下的强大能力。

## 功能一览

| 功能 | 说明 | Hy3 核心能力 |
|:---|:---|:---|
| 💬 **AI 对话** | 支持深度推理模式切换的流式对话 | 推理 (`reasoning_effort`) |
| ✍️ **论文润色** | 三种模式：学术润色 / 精简压缩 / 中英互译 | 推理 + 长文生成 |

## 技术亮点

- **全线流式输出**：基于 SSE (Server-Sent Events) 的实时 token 流
- **推理模式切换**：一键开启 `reasoning_effort=high` 深度思维链
- **多 Provider 支持**：预置自建服务、OpenRouter、自定义三种配置
- **API 连接测试**：一键检测 Hy3 服务可用性
- **纯前端实现**：HTML + CSS + JS，零依赖，直接打开即用
- **响应式设计**：适配桌面与移动端

## 快速开始

**前置条件**：需要一个可访问的 Hy3 OpenAI 兼容 API 端点（自建 vLLM/SGLang、OpenRouter 等）。

```bash
# 方式 1：直接用浏览器打开 index.html

# 方式 2：HTTP server（推荐，避免跨域）
npx serve .
# 或
python3 -m http.server 8080
```

打开后，在左侧「API 配置」面板填入：

| 字段 | 自建服务 | OpenRouter |
|:---|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` | `https://openrouter.ai/api/v1` |
| API Key | `EMPTY` | `sk-or-v1-你的密钥` |
| Model | `hy3` | `tencent/hy3` |

点击**测试连接**确认可用。

## 使用示例

- **对话模式**：选择「AI 对话」标签 →（可选）开启「深度推理」→ 输入问题 → Enter 发送
- **论文润色**：选择「论文润色」标签 → 粘贴文本 → 选模式 → 点击「开始润色」→ 复制/下载结果

## 文件结构

```
demo/
├── index.html    # 主页面（完整 UI 布局）
├── style.css     # 样式（渐变 + 动画 + 响应式）
├── script.js     # 交互逻辑（流式 API + 背景动画）
└── README.md     # 本文件
```

## 参考

- [Hy3 GitHub](https://github.com/Tencent-Hunyuan/Hy3)
- [Hy3 集成指南](../integrations/README.md)
