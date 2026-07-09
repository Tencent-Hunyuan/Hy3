# Hy3-CLI — 自然语言转 shell 命令的终端助手（由 Hy3 驱动）

> **犀牛鸟 2026 实战 issue #4** 作品 · 独立应用仓库

- **应用仓库：** https://github.com/yanghuicode/hy3-cli
- **提交 PR：** https://github.com/Tencent-Hunyuan/Hy3/pull/28 （目标分支 `rhinobird2026`）
- **作者：** yanghuicode
- **验证状态：** ✅ 已使用真实 Hy3 端点端到端跑通（非 mock）

---

## 1. Hy3 在系统中承担的角色

全程通过 **Hy3 的 `/chat/completions` HTTP API** 调用模型（OpenAI 兼容协议），
应用本身**不做训练 / 微调 / 本地推理部署**。Hy3 负责：

1. **意图理解** —— 把中文自然语言翻译成具体、可执行的 shell 命令；
2. **命令生成** —— 输出结构化 JSON：`{command, explanation, risk_level, caveats}`；
3. **命令解释** —— 用中文说明命令的作用与注意事项；
4. **风险初判** —— 给出 `low / medium / high` 风险等级供本地安全门禁参考。

本地代码（Python 标准库，零第三方依赖）独立负责：
- **安全门禁**：规则引擎识别危险命令（`rm -rf`、`dd`、`mkfs`、fork 炸弹、`taskkill /F`、`Stop-Process -Force` 等），高风险必须二次确认；
- **跨平台执行**：Windows 经临时脚本路由执行模型给出的 PowerShell 命令，macOS/Linux 走 shell；
- **交互与历史**：`chat` 多轮模式、历史记录落盘；
- **离线 mock**：无 API key 时也能跑通整条交互链路，便于评审与开发。

---

## 2. 如何运行 / 验证

```bash
git clone https://github.com/yanghuicode/hy3-cli
cd hy3-cli
python3 -m hy3cli --explain "找出当前目录下最近7天修改、大于100MB的文件"
python3 -m hy3cli chat          # 交互模式
python3 -m unittest discover    # 12 项单测
```

真实接入（作者已配好默认值，可直接用，或填 `.env` 覆盖）：

```
HY3_BASE_URL=http://101.43.51.108:3000/v1
HY3_API_KEY=<活动专用 key>
HY3_MODEL=hunyuan-3.0-free
```

> **推理模型注意**：`hunyuan-3.0-free` 是推理型模型，会在输出前消耗大量 token 思考。
> 应用已内置 `max_tokens=4096` 与瞬时错误自动重试，确保最终 JSON 不被截断。

---

## 3. 两个端到端 Demo（均已在真实 Hy3 上验证）

仓库内 `demo/real-session.txt` 为真实输出记录。

**Demo 1 — 文件检索（解释模式，低风险）**
```
$ hy3cli --explain "找出当前目录下最近7天修改、大于100MB的文件"
→ Hy3 生成： Get-ChildItem . -File -Recurse -ErrorAction SilentlyContinue |
              Where-Object { $_.Length -gt 100MB -and $_.LastWriteTime -gt (Get-Date).AddDays(-7) }
→ 风险等级：LOW
```

**Demo 2 — 端口排查（解释模式，中风险 + 安全确认）**
```
$ hy3cli --explain "查看占用 8080 端口的进程并杀掉"
→ Hy3 生成： Get-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess |
              Stop-Process -Force
→ 风险等级：MEDIUM（含强制结束进程，需用户确认）
```

**Demo 3（额外）— 真实执行（端到端闭环）**
```
$ hy3cli -y "列出当前目录下的文件"
→ Hy3 生成： Get-ChildItem
→ 经 PowerShell 路由真实执行，列出目录文件
```

---

## 4. 哪些代码块由 CodeBuddy / WorkBuddy 协作完成

- `hy3cli/client.py`：Hy3 OpenAI 兼容客户端、JSON 解析与 mock 模式（初版由 CodeBuddy 生成，后补充空内容回退解析与重试）。
- `hy3cli/safety.py`：危险命令规则集（由 WorkBuddy 建议并整理）。
- `hy3cli/assistant.py`：NL→命令主流程与交互模式（由 CodeBuddy 协助搭建骨架）。
- `README.md` 与 `demo/record.sh`：由 WorkBuddy 撰写。

**本次真实接入修复（作者完成，基于真实端点实测）：**
- `config.py`：默认 endpoint / 模型指向真实 RhinoBird Hy3；新增 `HY3_MAX_TOKENS=4096`、`HY3_RETRIES`；
- `client.py`：发送 `max_tokens`、best-effort 关闭思考、空内容从 `reasoning_content` 兜底、瞬时错误重试；
- `assistant.py` / `__main__.py`：Windows 命令经临时脚本路由执行，模型给出的 PowerShell 命令可真正运行；
- `safety.py`：将 `taskkill /F` 与 `Stop-Process -Force` 标注为中风险。

---

## 5. 活动要求对照

| 要求 | 满足 |
| --- | --- |
| 全程通过 API 调用 Hy3，不训练/部署 | ✅ |
| 至少 1 个可交互前端（Web/CLI/IDE 插件） | ✅ CLI（含 chat 交互模式） |
| 至少 2 个端到端 demo + ≤2min 视频/GIF | ✅ 已跑通 3 段真实 demo；视频录制脚本 `demo/record.sh` 在作者本机产出 |
| 项目开源 + README 写明 Hy3 角色 | ✅ |
| 基于 `rhinobird2026` 开发并提交 PR | ✅ PR #28 |
| README 记录 CodeBuddy 协作代码块 | ✅ |
