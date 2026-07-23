# Hy3 Evidence Board

> English: [README.en.md](README.en.md)

Evidence Board 是一个小而完整的 Hy3 Agent 应用：模型必须先调用 `search_knowledge_base`，服务端执行只读检索，再把证据回传给模型生成带来源报告。

![8 秒离线交互演示](../assets/evidence-board-demo.gif)

## 展示的 Hy3 核心能力

- OpenAI-compatible tool calling
- 基于证据的多轮 Agent 循环
- `no_think / low / high` 推理强度映射
- 长文整理与来源标注

## 安全设计

- API Key 只从服务端环境变量读取，不传给浏览器、不写 `localStorage`。
- 唯一工具是只读的本地知识库检索，模型不能执行 shell 或任意文件读取。
- 最多 3 轮工具调用，请求体限制 32 KiB，问题限制 10～500 字。
- 离线模式使用确定性 `DemoProvider`，页面和响应均明确标注“未调用 Hy3”。

## 运行

### 离线模式（无需 Key）

```bash
cd issue2/demo
HY3_DEMO_MODE=1 python3 server.py
```

打开 <http://127.0.0.1:8765>。

### OpenRouter 实时 Hy3

```bash
export HY3_PROVIDER=openrouter
export HY3_API_KEY='sk-or-v1-...'
export HY3_MODEL=tencent/hy3
python3 server.py
```

### 自建 vLLM/SGLang

```bash
export HY3_PROVIDER=selfhost
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_API_KEY=EMPTY
export HY3_MODEL=hy3
python3 server.py
```

自建服务必须按 Hy3 README 启用对应的 tool-call parser。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 server.py --check
```

`--check` 只检查离线工具链，不读取环境中的 Key，也不发网络请求。

## 目录

```text
demo/
├── evidence_board.py   # 检索、Provider 与 Agent 循环
├── server.py           # 标准库 HTTP 服务/API
├── static/             # HTML/CSS/JS
├── knowledge/          # 带原始 URL 的本地资料
├── tests/              # 单元与 HTTP 冒烟测试
└── .env.example        # 变量名示例，不含真实 Key
```

## 独立仓库交付

本目录不依赖 Hy3 主仓库中的 Python 包，可直接复制为独立仓库并使用 Apache-2.0 兼容许可发布。当前任务未获授权创建远程仓库或上传视频，因此只准备可独立发布的源码；发布后在集成索引中替换为远程地址，并录制 ≤1 分钟的实时 Hy3 演示。
