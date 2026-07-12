# Hy3 Review Workbench

一个面向代码变更的轻量 Web 工作台：粘贴 unified diff，使用 Hy3 生成按严重程度排序的代码审查或针对性的测试计划。

## Hy3's role

Hy3 是系统中的核心推理引擎。应用把代码 diff、业务上下文和审查目标发送到 Hy3 OpenAI-compatible API；Hy3 负责理解代码变化、识别正确性/安全性/可靠性风险、解释影响并生成测试建议。FastAPI 层只负责输入校验、提示词复用、API 调用和脱敏错误处理，不包含训练、微调或本地推理。

```text
Browser -> FastAPI -> existing prompt builders -> Hy3 API
        <- JSON/markdown review or test plan <-
```

## Run locally

要求 Python 3.10+，并准备一个 Hy3-compatible API endpoint。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/review_workbench/requirements.txt
cp .env.example .env
```

在 `.env` 中选择一种 API 配置。OpenRouter 示例：

```bash
HY3_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
HY3_MODEL=tencent/hy3:free
HY3_REASONING_EFFORT=no_think
```

启动应用：

```bash
uvicorn apps.review_workbench.app:app --reload --port 8008
```

打开 `http://127.0.0.1:8008`。API key 仅由服务端从环境变量或 `.env` 读取，不会进入页面、响应或错误信息。

## Demo 1: Payment security review

目标时长约 45 秒。

1. 在 `Demo case` 选择 `Payment security regression`。
2. 保持 `Code review` 和 `Balanced`，点击 `Run Hy3 review`。
3. 展示 Hy3 对 token 日志泄露、无界递归重试、超时策略和缺失测试的分级分析。
4. 点击 `Copy`，展示结果可直接进入 PR 评论。

## Demo 2: Retry test plan

目标时长约 45 秒。

1. 在 `Demo case` 选择 `Retry reliability gap`，页面自动切换到 `Test plan`。
2. 保持 `pytest` 与 `High`，点击 `Build test plan`。
3. 展示 Hy3 生成的重试次数、异常分类、退避、最终失败和回归测试建议。
4. 简短展示移动端或窄窗口下的单栏布局。

两段可连续录制，总时长控制在两分钟内。提交前将视频或 GIF 放入 `apps/review_workbench/assets/`，并在本节加入相对链接。

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/status` | 返回脱敏后的模型连接状态 |
| `GET /api/examples` | 返回两个固定 Demo diff |
| `POST /api/review` | 调用 Hy3 生成代码审查 |
| `POST /api/tests` | 调用 Hy3 生成测试计划 |

每个 diff 最大 24,000 字符。外部 API 未配置密钥时返回 `503`；超时返回 `504`；其他上游错误返回不包含内部细节的 `502`。

## Tests

```bash
PYTHONPATH=mcp_servers/code_review/src:. pytest -q \
  apps/review_workbench/tests \
  mcp_servers/code_review/tests
node --check apps/review_workbench/static/app.js
```

## CodeBuddy collaboration

本应用与 CodeBuddy 协作完成的代码块记录如下：

- `app.py` / `schemas.py`：FastAPI 路由、Hy3 客户端复用、输入边界与错误脱敏。
- `examples.py`：支付安全审查与重试测试计划两个端到端 Demo。
- `static/`：双模式工作台、响应式布局、安全结果格式化和复制交互。
- `tests/test_app.py`：API 契约、密钥脱敏、异常处理、Demo 和静态资源测试。
- 本 README：运行方式、Hy3 角色、演示与录制脚本。

现有 `mcp_servers/code_review/` 保持不变，Web 应用复用其 Hy3 API 客户端和提示词实现。
