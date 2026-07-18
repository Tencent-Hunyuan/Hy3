# Reasoning Mode（思考过程开 / 关对比）

## 目标

本示例使用同一个问题，对比 `reasoning_effort="no_think"` 与 `reasoning_effort="high"` 的响应正文、独立思考字段和 Token 用量。

## 前置条件

- Python 3.10+
- OpenAI Python SDK `openai>=1.0.0`，环境变量加载库 `python-dotenv>=1.0.0`
- 环境变量：`HY3_BASE_URL`、`HY3_API_KEY`、`HY3_MODEL`；可从 `quickstart/.env.example` 复制为 `quickstart/.env`
- 模型能力要求：Hy3 chat template 支持 `no_think`、`low`、`high`；vLLM 需启用 `--reasoning-parser hy_v3`，SGLang 需启用 `--reasoning-parser hunyuan`

安装依赖：

```bash
python -m pip install "openai>=1.0.0" "python-dotenv>=1.0.0"
```

## 完整请求

```python
PROMPT = "列出 1 到 20 中所有能被 3 整除的整数，并计算它们的和。"

def run_mode(reasoning_effort):
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=128,
        extra_body={
            "chat_template_kwargs": {
                "reasoning_effort": reasoning_effort,
            }
        },
    )

no_think_response = run_mode("no_think")
high_response = run_mode("high")
```

## 完整 Response 解析

Hy3 的推理解析器可能把思考过程放在扩展字段 `reasoning_content` 中。该字段不属于所有 OpenAI 兼容服务都具备的通用字段，因此脚本同时尝试 SDK 对象属性和 Pydantic 的 `model_extra`。

```python
def extract_reasoning_content(message):
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning:
        return reasoning
    model_extra = getattr(message, "model_extra", None) or {}
    return model_extra.get("reasoning_content")

for choice in response.choices:
    print(choice.finish_reason)
    print(extract_reasoning_content(choice.message))
    print(choice.message.content)
```

脚本还解析响应 ID、模型与 Token 用量。如果 `high` 没有返回独立思考字段，应检查服务端 reasoning parser、框架版本和原始 JSON；不要仅据此断定模型没有进行思考。

## 运行方式

在 `quickstart/` 目录执行：

```bash
python examples/05_reasoning_mode/reasoning_mode.py
```

## 示例输出

下面的思考内容仅为截断后的格式示意，实际内容、长度和 Token 数由模型决定。

```text
=== 思考关闭：no_think ===
id=chatcmpl-no-think
model=hy3
choice[0].finish_reason=stop
choice[0].reasoning_content=<未返回独立思考字段>
choice[0].content=能被 3 整除的整数是 3、6、9、12、15、18，和为 63。
usage: prompt=24, completion=25, total=49

=== 思考开启：high ===
id=chatcmpl-high
model=hy3
choice[0].finish_reason=stop
choice[0].reasoning_content=先列出 3 的倍数，再逐项求和……
choice[0].content=3、6、9、12、15、18 的总和是 63。
usage: prompt=24, completion=54, total=78
```
