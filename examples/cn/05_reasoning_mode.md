# 05 思考模式（Reasoning Mode）

## 简介

Hy3 支持通过思考模式开关切换是否进行链式思考（Chain-of-Thought）。本示例对比两种模式：

- **思考关闭**：不进行链式思考，直接给出回答。响应快，适合日常对话。
- **思考开启**：进行深度链式思考，先输出逐步推理过程（`reasoning_content`），再给最终答案（`content`）。适合数学、代码、复杂逻辑推理等任务。

示例用同一道简单的数学分析题，分别在思考关闭与思考开启下调用模型，并打印对比两者的 `reasoning_content`（思维链）与 `content`（最终答案）。

---

## 前置条件

1. Hy3 服务可用（二选一）：
   - **云端 TokenHub API**：base_url `https://tokenhub.tencentmaas.com/v1`，需在 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey) 申请 API Key。
   - **本地 vLLM / SGLang 部署**：base_url `http://127.0.0.1:8000/v1`。

2. **若希望 `reasoning_content` 被独立分离出来**：
   - 云端 TokenHub API：使用 `thinking` 参数即可自动分离（本示例已包含）。
   - 本地 vLLM：启动时加 `--reasoning-parser hy_v3`
   - 本地 SGLang：启动时加 `--reasoning-parser hunyuan`

   若本地未启用 reasoning 解析器，思考内容可能混入 `content` 中，`reasoning_content` 字段为空。

3. 安装依赖：
   ```bash
   pip install openai
   ```

4. 连接信息通过环境变量配置（默认值适用于本地部署）：
   ```bash
   set HY3_BASE_URL=http://127.0.0.1:8000/v1
   set HY3_API_KEY=EMPTY
   ```
   若使用云端 TokenHub API：
   ```bash
   set HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
   set HY3_API_KEY=sk-你的APIKey
   ```

---

## 完整请求

> 完整可运行脚本位于 `../en/05_reasoning_mode.py`。

```python
"""Hy3 Example 05: Reasoning mode comparison (no_think / low / high).

Sends dual-compatible parameters for local and cloud:
  - Cloud TokenHub: thinking:{type: enabled|disabled}
  - Local vLLM/SGLang: chat_template_kwargs.reasoning_effort (no_think|low|high)

When thinking is enabled, chain-of-thought appears in message.reasoning_content
(local requires --reasoning-parser hy_v3 / hunyuan).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import (  # noqa: E402
    chat_completion,
    extract_reasoning_and_content,
    get_config,
    make_client,
)

PROMPT = (
    "小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。"
)

MODES = (
    ("no_think", "Mode 1: Thinking off (no_think) — direct answer"),
    ("low", "Mode 2: Light thinking (low)"),
    ("high", "Mode 3: Deep thinking (high)"),
)


def run_mode(client, reasoning: str, title: str):
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"[User Question]\n{PROMPT}\n")

    # high mode can emit long CoT; give it more room
    max_tokens = 8192 if reasoning == "high" else 2048
    response = chat_completion(
        client,
        [{"role": "user", "content": PROMPT}],
        reasoning=reasoning,
        max_tokens=max_tokens,
    )
    message = response.choices[0].message
    reasoning_content, content = extract_reasoning_and_content(message)

    if reasoning_content:
        print("[Chain-of-thought reasoning_content]")
        print(reasoning_content)
        print()
    else:
        print(
            "[Chain-of-thought reasoning_content] "
            "(none; thinking disabled, or server has no reasoning parser)\n"
        )

    print("[Final answer content]")
    print(content)
    if response.usage:
        print(
            f"\n[Usage] prompt={response.usage.prompt_tokens} "
            f"completion={response.usage.completion_tokens} "
            f"total={response.usage.total_tokens}"
        )
    print()


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    for mode, title in MODES:
        run_mode(client, mode, title)

    print("=" * 70)
    print("[Comparison summary]")
    print("=" * 70)
    print("no_think: direct answer, lowest latency — everyday chat.")
    print("low:      light chain-of-thought — structured / multi-constraint tasks.")
    print("high:     deep CoT — math / code / hard reasoning (raise max_tokens).")
    print()
    print("If reasoning_content is empty when thinking is on, check:")
    print("  - Cloud TokenHub: thinking parameter is already sent by common.build_extra_body")
    print("  - Local vLLM:   add --reasoning-parser hy_v3 at startup")
    print("  - Local SGLang: add --reasoning-parser hunyuan at startup")


if __name__ == "__main__":
    main()
```

---

## 完整 response 解析

### 1. 思考模式开关的传参方式

思考模式的传参方式因部署方式而异。本示例**同时发送两种参数**以兼容本地与云端：

```python
extra_body={
    # 云端 TokenHub API 的思考开关
    "thinking": {"type": "enabled"},   # "enabled" 开启 / "disabled" 关闭
    # 本地 vLLM/SGLang 部署的思考深度开关
    "chat_template_kwargs": {"reasoning_effort": "high"},  # "high" / "no_think"
}
```

- **云端 TokenHub API** 识别 `thinking` 字段，忽略 `chat_template_kwargs`。
- **本地 vLLM/SGLang** 识别 `chat_template_kwargs.reasoning_effort`，忽略 `thinking`。
- 两套参数同时发送互不干扰，实现一份代码兼容两种部署。

### 2. 云端 TokenHub API 的思考开关

| `thinking.type` | 行为 | 适用场景 |
|:---|:---|:---|
| `"disabled"` | 直接响应，不产生思维链 | 日常对话、简单问答 |
| `"enabled"`  | 深度链式思考，分离出 `reasoning_content` | 数学、代码、复杂逻辑推理 |

云端还支持 `reasoning_effort` 顶层参数控制推理深度（`low`/`high`，默认 `low`），详见 [深度思考文档](https://cloud.tencent.com/document/product/1823/131208)。

### 3. 本地部署的思考深度开关

| `reasoning_effort` | 行为 | 适用场景 |
|:---|:---|:---|
| `"no_think"` | 直接响应，不产生思维链（默认） | 日常对话、简单问答 |
| `"low"`      | 轻量级链式思考 | 中等复杂度的分析 |
| `"high"`     | 深度链式思考，思考更充分 | 数学、代码、复杂逻辑推理 |

### 4. 响应字段：`reasoning_content` 与 `content`

开启思考后，响应的 `message` 包含两个字段：

- **`reasoning_content`**：思维链（Chain-of-Thought），即模型的逐步推理过程。属于可选字段。
  - 云端 TokenHub API：使用 `thinking` 参数时自动分离。
  - 本地：需服务端启用 reasoning 解析器（vLLM `--reasoning-parser hy_v3`；SGLang `--reasoning-parser hunyuan`）。
- **`content`**：最终给用户的答案。

读取时应做兼容处理（`reasoning_content` 可能为 `None`）：

```python
reasoning_content = getattr(message, "reasoning_content", None)
if reasoning_content:
    print(reasoning_content)  # 思维链
print(message.content)        # 最终答案
```

> 若本地未启用 reasoning 解析器，思考过程可能会混在 `content` 中输出，`reasoning_content` 为空。

### 5. 适用场景建议

- **思考开启**：数学计算、代码生成与调试、多步逻辑推理、复杂规划类任务。思考更充分，但响应时间更长、token 消耗更多。
- **思考关闭**：闲聊、信息查询、格式化输出、对延迟敏感的场景。响应快、成本低。

本示例使用 `temperature=0.9`、`top_p=1.0`（官方推荐参数）。

---

## 示例输出
> 已于 **2026-07-18** 在腾讯云 **TokenHub** （`https://tokenhub.tencentmaas.com/v1`，`model=hy3`）实测。内容为模型生成，可能随调用变化；密钥已脱敏。

```text
模式: high（开启思考）
最终答案 content: 4
reasoning_content 存在: True（长度=89）
reasoning_content 预览:
小明有5个苹果。 分给3个朋友每人1个，分出去3个，剩下 5 - 3 = 2 个。 又买了2个，现在有 2 + 2 = 4 个。 题目问还有几个，只给数字答案。 所以答案是 4。
```
