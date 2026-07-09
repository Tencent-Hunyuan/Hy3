# Hy3-CLI — 自然语言转 shell 命令的终端助手

> 2026 犀牛鸟开源人才培养活动 · issue #4「Build a vibe-coded application powered by Hy3」
> 独立应用仓库：https://github.com/yanghuicode/hy3-cli

## 项目简介
Hy3-CLI 是一个**零依赖（仅 Python 标准库）**的命令行工具：把一句自然语言（中/英）变成**正确、带解释、标注风险等级**的 shell 命令，并内置安全门禁与交互模式（chat）。

## Hy3 在系统中承担的角色
全程通过 Hy3 的 OpenAI 兼容 `/chat/completions` HTTP API 调用模型，**不做训练 / 微调 / 本地推理部署**。
- Hy3 负责「理解 + 生成」：将自然语言意图翻译成单条 shell 命令，并输出 `{command, explanation, risk_level, caveats}` 结构化 JSON。
- 本地代码负责「安全 + 交互 + 执行」：独立安全规则门禁、确认流程、跨平台适配（Windows PowerShell / Linux·macOS bash）与历史记录。

## 两个端到端 Demo 流程
1. **文件检索（低风险，直接执行）**：`hy3cli "找出当前目录下最近7天修改、大于100MB的文件"` → 生成 find 命令 → 列出文件。
2. **端口排查（中风险，带确认）**：`hy3cli "查看占用 8080 端口的进程并杀掉"` → 生成 lsof 命令 → 中风险提示确认后执行。

演示视频（≤2min）请按仓库 `demo/record.sh`（asciinema）录制，详见 README。

## 快速开始
```bash
git clone https://github.com/yanghuicode/hy3-cli
cd hy3-cli && cp .env.example .env   # 填入 HY3_API_KEY / HY3_BASE_URL / HY3_MODEL
python3 -m hy3cli "递归统计每个子目录的大小"
```

## 与 CodeBuddy / WorkBuddy 的协作
本仓库为「vibe-coded」作品，下列模块由 CodeBuddy / WorkBuddy（基于 Hy3）协助生成或重构：`hy3cli/client.py`（Hy3 客户端与 mock）、`hy3cli/safety.py`（安全规则）、`hy3cli/assistant.py`（主流程）及 README。
