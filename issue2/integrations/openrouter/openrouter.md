# 在 OpenRouter 中使用 Hy3

> English: [openrouter.en.md](openrouter.en.md) · [返回索引](../README.md)

OpenRouter 适合不自建 8 卡推理服务、希望直接按量调用 Hy3 的用户。以下字段于 2026-07-23 按 [OpenRouter 的 Hy3 模型页](https://openrouter.ai/tencent/hy3)核对。

## 要求

- OpenRouter 账号和可用 API Key
- `curl`，或 Python 3.10+（小作品本身仅使用标准库）
- 模型 ID：`tencent/hy3`；如要试用免费路由，可在模型页确认当时是否仍提供 `tencent/hy3:free`

## 配置

```bash
export HY3_PROVIDER=openrouter
export HY3_BASE_URL=https://openrouter.ai/api/v1
export HY3_MODEL=tencent/hy3
export HY3_API_KEY='sk-or-v1-...'
```

不要把 Key 写入脚本或提交到 Git。OpenRouter 使用 OpenAI 兼容的 `POST /chat/completions`；推理强度可用 `reasoning.effort` 控制。

## 第一次对话

```bash
curl "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "tencent/hy3",
    "messages": [{"role": "user", "content": "只回复 READY，并说明你的模型 ID。"}],
    "temperature": 0.9,
    "reasoning": {"effort": "low"}
  }'
```

验收：HTTP 200，`choices[0].message.content` 非空；不要仅以控制台出现请求记录判定成功。

## 端到端任务：证据研究板

1. 启动本仓库的小作品：

   ```bash
   cd issue2/demo
   python3 server.py
   ```

2. 打开 `http://127.0.0.1:8765`，确认页头显示“实时 Hy3”。
3. 输入：

   ```text
   根据内置资料解释 Hy3 为什么适合 Agent，并列出模型规模、上下文和部署时的工具调用要求。每条结论必须带来源。
   ```

4. 验收响应中的工具轨迹：第一次模型响应调用 `search_knowledge_base`，服务端回传检索片段，第二次响应给出带来源的报告。

本地无 Key 时可用 `HY3_DEMO_MODE=1 python3 server.py` 检查界面和检索链路，但页面会明确标为离线模式，不能把该输出当成 Hy3 运行证据。

![Evidence Board 离线运行截图](../../assets/evidence-board-offline.png)

## 常见问题

| 症状 | 检查 |
|:---|:---|
| `401` | Key 是否完整、是否带多余空格、账户额度是否可用 |
| `404 model not found` | 必须使用 `tencent/hy3`，不是自建端点的 `hy3` |
| 无工具调用 | 请求是否包含 `tools`；模型路由是否支持 tool calling；先用低复杂度单工具任务排查 |
| 输出慢 | 深度推理和长输出会增加延迟；先改为 `low` 并缩短问题 |
| 费用不可控 | 在 OpenRouter 设置 Key 限额，并在响应 `usage` 中核对 token |

## 证据清单

提交前请另行录制一次 ≤1 分钟的实时调用：画面应同时包含模型 ID、问题、工具轨迹和最终报告，并遮蔽 Key。本仓库不伪造该在线证据。
