# 05 思考模式（Reasoning Mode）

## 简介

Hy3 支持通过 `reasoning_effort` 参数切换思考深度。本示例对比两种模式：

- **`no_think`**：不进行链式思考，直接给出回答。响应快，适合日常对话（默认模式）。
- **`high`**：进行深度链式思考（Chain-of-Thought），先输出逐步推理过程，再给最终答案。适合数学、代码、复杂逻辑推理等任务。

示例用同一道简单的数学分析题，分别在 `no_think` 与 `high` 下调用模型，并打印对比两者的 `reasoning_content`（思维链）与 `content`（最终答案）。

---

## 前置条件

1. 已通过 vLLM 或 SGLang 启动 Hy3 服务。

2. **若希望 `reasoning_content` 被独立分离出来**，服务端必须启用 reasoning 解析器：
   - vLLM：`--reasoning-parser hy_v3`
   - SGLang：`--reasoning-parser hunyuan`

   若未启用，思考内容可能混入 `content` 中，`reasoning_content` 字段为空。

3. 安装依赖：
   ```bash
   pip install openai
   ```

4. 连接信息通过环境变量配置（默认值适用于本地部署）：
   ```bash
   set HY3_BASE_URL=http://127.0.0.1:8000/v1
   set HY3_API_KEY=EMPTY
   ```

---

## 完整请求

```python
"""
Hy3 思考模式（Reasoning Mode）对比示例
=====================================

演示通过 reasoning_effort 切换 Hy3 的思考深度，对比两种模式：
  - no_think：直接响应，不进行链式思考（适合日常对话，默认）
  - high    ：深度链式思考，适合数学/代码/复杂推理任务

reasoning_effort 通过 extra_body={"chat_template_kwargs": {"reasoning_effort": ...}} 传入。
开启思考时，响应可能在 message.reasoning_content 字段中返回思维链（CoT），
最终答案在 message.content 中。reasoning_content 是否独立分离取决于服务端
是否启用了 reasoning 解析器（vLLM: --reasoning-parser hy_v3；SGLang: --reasoning-parser hunyuan）。

连接信息通过环境变量配置（带默认值）：
  HY3_BASE_URL  默认 http://127.0.0.1:8000/v1
  HY3_API_KEY   默认 EMPTY
"""

import os

from openai import OpenAI

# 通过环境变量初始化客户端（带默认值），方便切换部署地址
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"

# 适合触发推理的提示词：带简单数学运算的逐步分析题
PROMPT = "小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。"


def chat(reasoning_effort: str):
    """以指定 reasoning_effort 调用 Hy3，返回完整 message 对象。"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        extra_body={
            "chat_template_kwargs": {"reasoning_effort": reasoning_effort}
        },
    )
    return response.choices[0].message


def print_section(title, message):
    """统一打印某次调用的 reasoning_content（如有）与 content。"""
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"【用户提问】\n{PROMPT}\n")

    # reasoning_content 是可选字段：服务端启用 reasoning 解析器后才会分离出来
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content:
        print("【思维链 reasoning_content】")
        print(reasoning_content)
        print()
    else:
        print("【思维链 reasoning_content】(无，未分离或该模式不产生思考内容)\n")

    print("【最终回答 content】")
    print(message.content)
    print()


def main():
    # ---- 调用 1：no_think，直接响应 ----
    msg_no_think = chat("no_think")
    print_section("模式一：reasoning_effort = no_think（直接响应）", msg_no_think)

    # ---- 调用 2：high，深度链式思考 ----
    msg_high = chat("high")
    print_section("模式二：reasoning_effort = high（深度思考）", msg_high)

    # ---- 对比小结 ----
    print("=" * 70)
    print("【对比小结】")
    print("=" * 70)
    print("no_think：直接给出答案，无思维链，响应快，适合日常对话。")
    print("high    ：先输出逐步推理（reasoning_content），再给最终答案，")
    print("          适合数学/代码/复杂逻辑推理任务。")
    print()
    print("提示：若 reasoning_content 始终为空，请确认服务端启用了 reasoning 解析器：")
    print("  vLLM:   --reasoning-parser hy_v3")
    print("  SGLang: --reasoning-parser hunyuan")


if __name__ == "__main__":
    main()
```

---

## 完整 response 解析

### 1. `reasoning_effort` 的传参方式

`reasoning_effort` 不是顶层参数，而是通过 `extra_body` 透传到聊天模板：

```python
extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
```

### 2. 可选取值

| 值         | 含义                                       | 适用场景                     |
|:----------|:-------------------------------------------|:-----------------------------|
| `no_think` | 直接响应，不产生思维链（**默认**）          | 日常对话、简单问答           |
| `low`      | 轻量级链式思考                              | 中等复杂度的分析             |
| `high`     | 深度链式思考，思考更充分                    | 数学、代码、复杂逻辑推理     |

### 3. 响应字段：`reasoning_content` 与 `content`

开启思考后，响应的 `message` 可能包含两个字段：

- **`reasoning_content`**：思维链（Chain-of-Thought），即模型的逐步推理过程。属于可选字段，**只有服务端启用了 reasoning 解析器时才会被独立分离**：
  - vLLM：`--reasoning-parser hy_v3`
  - SGLang：`--reasoning-parser hunyuan`
- **`content`**：最终给用户的答案。

读取时应做兼容处理（`reasoning_content` 可能为 `None`）：

```python
reasoning_content = getattr(message, "reasoning_content", None)
if reasoning_content:
    print(reasoning_content)  # 思维链
print(message.content)        # 最终答案
```

> 若未启用 reasoning 解析器，思考过程可能会混在 `content` 中输出，`reasoning_content` 为空。

### 4. 适用场景建议

- **`high`**：数学计算、代码生成与调试、多步逻辑推理、复杂规划类任务。思考更充分，但响应时间更长、token 消耗更多。
- **`no_think`**：闲聊、信息查询、格式化输出、对延迟敏感的场景。响应快、成本低。
- **`low`**：介于两者之间，适合需要一定分析但不必深度展开的任务。

本示例使用 `temperature=0.9`、`top_p=1.0`（官方推荐参数）。

---

## 示例输出

> 以下为示例性输出（非真实运行结果），用于展示两种模式的打印格式与差异。

```text
======================================================================
模式一：reasoning_effort = no_think（直接响应）
======================================================================
【用户提问】
小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。

【思维链 reasoning_content】(无，未分离或该模式不产生思考内容)

【最终回答 content】
小明原有 5 个苹果，分给 3 个朋友每人 1 个共分出 3 个，剩下 2 个；
又买了 2 个，所以现在有 2 + 2 = 4 个苹果。

======================================================================
模式二：reasoning_effort = high（深度思考）
======================================================================
【用户提问】
小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。

【思维链 reasoning_content】
让我逐步分析这道题：
1. 小明最初有 5 个苹果。
2. 分给 3 个朋友，每人 1 个，一共分出去 3 × 1 = 3 个。
3. 分完后，小明剩下 5 - 3 = 2 个。
4. 接着又买了 2 个，所以现在有 2 + 2 = 4 个。
因此最终答案是 4 个苹果。

【最终回答 content】
小明现在还有 4 个苹果。

分析过程：
1. 原有 5 个苹果；
2. 分给 3 个朋友每人 1 个，共分出 3 个，剩 5 - 3 = 2 个；
3. 又买了 2 个，2 + 2 = 4 个。
所以最终小明有 4 个苹果。

======================================================================
【对比小结】
======================================================================
no_think：直接给出答案，无思维链，响应快，适合日常对话。
high    ：先输出逐步推理（reasoning_content），再给最终答案，
          适合数学/代码/复杂逻辑推理任务。

提示：若 reasoning_content 始终为空，请确认服务端启用了 reasoning 解析器：
  vLLM:   --reasoning-parser hy_v3
  SGLang: --reasoning-parser hunyuan
```
