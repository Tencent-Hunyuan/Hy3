# 05 Reasoning Mode：思考过程开/关对比

Hy3 支持在生成最终答案前输出推理过程。本示例对比开启与关闭思考模式的效果，并演示如何读取 `reasoning_content`。

## 完整请求

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

PROMPT = "9.11 和 9.8 哪个更大？请说明原因。"


def ask_with_thinking(enabled: bool):
    extra_body = {"thinking": {"type": "enabled" if enabled else "disabled"}}
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.3,
        max_tokens=512,
        extra_body=extra_body,
    )

    msg = response.choices[0].message
    mode = "开启思考" if enabled else "关闭思考"
    print(f"=== {mode} ===")

    reasoning = getattr(msg, "reasoning_content", None)
    if reasoning:
        print("【思考过程】")
        print(reasoning)
        print("\n【最终回答】")
    print(msg.content)
    print()


ask_with_thinking(False)
ask_with_thinking(True)
```

## Response 解析

- 关闭思考模式时，模型直接输出最终答案，`reasoning_content` 为空。
- 开启思考模式时，响应额外包含 `reasoning_content` 字段，展示模型的中间推理过程。
- 使用 OpenAI Python SDK 时，`reasoning_content` 未在类型中声明，需用 `getattr` 访问。

## 示例输出

```text
=== 关闭思考 ===
9.8 更大。因为比较一位小数时，9.8 表示 98/10，而 9.11 表示 911/100；统一为百分位后，9.80 > 9.11。

=== 开启思考 ===
【思考过程】
用户问 9.11 和 9.8 哪个更大。注意这里不是版本号比较，而是数值比较。
9.11 = 9 + 11/100 = 9.11
9.8 = 9 + 8/10 = 9.80
9.80 > 9.11，所以 9.8 更大。

【最终回答】
9.8 更大。因为 9.8 = 9.80，而 9.80 > 9.11。
```

## 要点提示

1. 思考模式默认关闭，适合需要快速响应的场景。
2. 数学推导、代码调试、复杂逻辑分析建议开启思考模式。
3. 若发生工具调用，后续轮次需要完整回传 `reasoning_content`（如适用）。
4. 某些平台/部署方式使用 `reasoning_effort` 控制强度（`no_think` / `low` / `high`），TokenHub 官方接口优先使用 `thinking` 开关。
