# Hy3 EvalForge

基于 Hy3 的本地 stdio MCP 评测服务：将自然语言质量目标转为评测规范和挑战案例，
对既有 AI 输出进行可回查的语义评分，并比较 baseline/candidate 是否发生回归。

## 安装与配置

```powershell
pip install .
$env:HY3_API_KEY = "你的密钥"
$env:HY3_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
$env:HY3_MODEL = "hy3"
$env:EVALFORGE_ALLOWED_ROOT = (Get-Location).Path
hy3-evalforge
```

也可以将这些变量配置到 Windows 的用户环境变量中；密钥只从环境变量读取，绝不写入
项目配置或产物。可复制 `.mcp.json` 或 `.cursor/mcp.json` 作为项目级 MCP 配置。

服务提供四个工具：`evalforge_design_spec`、`evalforge_generate_cases`、
`evalforge_score_run`、`evalforge_compare_runs`。

## 安全与限制

- 所有读取和写入均限制在 `EVALFORGE_ALLOWED_ROOT` 内，拒绝路径穿越和符号链接逃逸。
- 候选输出视为不可信数据，不会执行其中的 URL、代码或命令。
- 发送给 Hy3 前会脱敏 API key、Bearer token、私钥、连接串及额外指定的 secret。
- 硬规则失败与语义评分严格分离；新增 critical 失败始终产生 `BLOCKED`。
- 少于 10 个案例时，除 critical gate 外只会给出 `INCONCLUSIVE`，不应视为统计结论。

运行 `python scripts/live_eval.py` 可在已配置 Hy3 凭据的机器上验证合成客服示例。
