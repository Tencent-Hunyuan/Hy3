# Hy3 Video Copilot

基于 [Hy3](https://github.com/Tencent-Hunyuan/Hy3)（腾讯混元快慢思考融合 MoE 模型）构建的 AI 视频剪辑助手。

## Hy3 在系统中承担的角色

Hy3 作为整个应用的 **大脑**：
- 理解用户自然语言描述的剪辑需求，生成结构化的剪辑计划
- 分析视频元数据，提供专业的剪辑建议
- 根据主题和风格生成完整的视频脚本
- 所有 AI 能力均通过 Hy3 API 调用实现，不涉及微调或本地推理

## 功能

| 功能 | 说明 |
|------|------|
| **智能剪辑** | 用自然语言描述剪辑需求 → Hy3 生成多步剪辑计划 → 通过 ffmpeg 执行 |
| **视频分析** | 上传视频 → Hy3 分析元数据并提供改进建议 |
| **脚本生成** | 输入主题 + 风格 → Hy3 生成包含时间线的完整视频脚本 |

## 快速开始

### 依赖

- Python >= 3.10
- 已安装 ffmpeg / ffprobe
- Hy3 API key

### 后端

```bash
cd hy3-video-copilot/backend
pip install -r requirements.txt
HY3_API_KEY=sk-xxx uvicorn main:app --reload --port 8000
```

### 前端

直接用浏览器打开 `hy3-video-copilot/frontend/index.html`（或用任意静态服务器托管）。

### 端到端 Demo

1. **智能剪辑流程**：上传视频 → 输入"剪掉前5秒并添加淡入" → 查看剪辑结果
2. **视频分析流程**：上传视频 → 点击"开始分析" → 阅读 Hy3 的专业分析报告

## 目录结构

```
hy3-video-copilot/
├── backend/
│   ├── main.py             # FastAPI 服务，4 个 API 端点
│   ├── hy3_client.py       # Hy3 API 封装
│   ├── video_processor.py  # 基于 ffmpeg 的视频处理
│   └── requirements.txt
├── frontend/
│   └── index.html          # 单页 React UI
├── demo/                   # Demo GIF
├── README.md
└── README_CN.md
```

## CodeBuddy 协作说明

以下代码块由 CodeBuddy 协作完成：
- `backend/main.py` — 接口设计及 Hy3 Prompt 工程
- `backend/video_processor.py` — ffmpeg 命令封装
- `frontend/index.html` — React UI 组件结构

## 许可证

Apache-2.0
