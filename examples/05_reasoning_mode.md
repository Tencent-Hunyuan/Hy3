# 示例 05：思考模式对比（no_think / high）

> 对应脚本：[`05_reasoning_mode.py`](05_reasoning_mode.py)

Hy3 支持“先思考再回答”。开启后，响应里会多一个 `reasoning_content` 字段，包含模型内部推理过程（**一般不直接展示给用户**，可用于调试或日志）。

## 控制方式（本地部署）

通过 `extra_body` 透传非标准参数：

```python
# 关闭思考（默认，最快）
extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
# 深度思考
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
```

> 需要服务端在启动时启用 reasoning parser 才能解析出 `reasoning_content`：vLLM 加 `--reasoning-parser hy_v3`，SGLang 加 `--reasoning-parser hunyuan`；否则该字段不存在（见 quickstart 第 9 节排查表）。

| 取值 | 适用场景 |
|---|---|
| `no_think` | 简单问答、翻译、格式转换 → 最快 |
| `low` | 一般推理任务 → 平衡 |
| `high` | 数学证明、复杂代码、多步规划 → 最深 |

## 完整请求

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "鸡兔同笼：共 35 只，94 只脚，鸡兔各几？"}],
    temperature=0.3,
    max_tokens=4096,
    extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},   # "no_think" 或 "high"
)
```

## 完整响应解析

`high` 模式下，`message.reasoning_content` 有值：

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "设鸡 x 只、兔 y 只，则 x+y=35，2x+4y=94……解得鸡 23 只、兔 12 只。",
      "reasoning_content": "x+y=35 → y=35-x；代入 2x+4(35-x)=94 → 2x+140-4x=94 → -2x=-46 → x=23……"
    },
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 22, "completion_tokens": 210, "total_tokens": 232}
}
```

| 字段 | 含义 |
|---|---|
| `message.reasoning_content` | 内部推理过程（`no_think` 时为 `null`） |
| `message.content` | 最终给用户的答案 |
| `usage` | `reasoning_content` 的 token 也计入用量，深度思考需调大 `max_tokens` |

> 多轮工具循环**且开启思考时**，建议把 `reasoning_content` 原样保留在 assistant 消息里（与 `content`、`tool_calls` 同级），以免后续轮次丢失上下文。

## 示例输出

> 以下输出由 **hy3** 捕获：`no_think` 的 `reasoning_tokens=0`（不思考），`high` 的 `reasoning_tokens=343`（正常推理）。本地部署（vLLM `--reasoning-parser hy_v3` / SGLang `--reasoning-parser hunyuan`）与云端 hy3 行为一致。

```
==================================================
reasoning_effort = no_think
==================================================
[思考过程] (无：no_think 模式不输出推理，或 reasoning parser 未启用)

[最终答案]
这是一个经典的“鸡兔同笼”问题，可以用假设法或方程来解。

**方法一：假设法**
1. 假设 35 只全是鸡，那么脚的总数应为：
   $35 \times 2 = 70$ 只脚
2. 实际有 94 只脚，多了：
   $94 - 70 = 24$ 只脚
3. 每把一只鸡换成一只兔，脚会增加：
   $4 - 2 = 2$ 只
4. 所以兔的数量为：
   $24 \div 2 = 12$ 只
5. 鸡的数量为：
   $35 - 12 = 23$ 只

**方法二：列方程**
设鸡有 $x$ 只，兔有 $y$ 只：
$$
\begin{cases}
x + y = 35 \\
2x + 4y = 94
\end{cases}
$$
由第一式得 $x = 35 - y$，代入第二式：
$$
2(35 - y) + 4y = 94 \\
70 - 2y + 4y = 94 \\
2y = 24 \\
y = 12
$$
所以 $x = 23$。

**答案：** 鸡有 **23 只**，兔有 **12 只**。
[Token 用量] CompletionUsage(completion_tokens=291, prompt_tokens=43, total_tokens=334, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=0, rejected_prediction_tokens=None), prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cached_tokens=0))

==================================================
reasoning_effort = high
==================================================
[思考过程] (前 300 字)
用户问了一个经典的中国古代数学问题：鸡兔同笼。
已知条件：
- 鸡和兔共 35 只。
- 脚共 94 只。
- 鸡有 2 只脚，兔有 4 只脚。
求：鸡和兔各有多少只？

设鸡有 x 只，兔有 y 只。
方程：
x + y = 35
2x + 4y = 94

解法1：代数法
由第一式得 x = 35 - y
代入第二式：2(35 - y) + 4y = 94
70 - 2y + 4y = 94
2y = 24
y = 12
x = 35 - 12 = 23
所以鸡有 23 只，兔有 12 只。

解法2：假设法（经典解法）
假设全是鸡，则脚有 35 * 2 = 70 只。
实际有 94 只脚...

[最终答案]
这是一个经典的“鸡兔同笼”问题。我们可以用假设法或方程法来解决。

### 方法一：假设法（经典解法）
1. **假设全是鸡**：如果 35 只全是鸡，那么每只鸡有 2 只脚，总脚数应该是 $35 \times 2 = 70$ 只。
2. **计算脚数差**：实际有 94 只脚，比假设多了 $94 - 70 = 24$ 只脚。
3. **换成兔子**：每把一只鸡换成一只兔子，脚的数量就会增加 $4 - 2 = 2$ 只。所以，兔子有 $24 \div 2 = 12$ 只。
4. **求鸡的数量**：鸡的数量就是 $35 - 12 = 23$ 只。

### 方法二：方程法
设鸡有 $x$ 只，兔有 $y$ 只。
根据题意列出方程组：
- $x + y = 35$ （总数）
- $2x + 4y = 94$ （脚数）

由第一个方程得 $x = 35 - y$，代入第二个方程：
$2(35 - y) + 4y = 94$
$70 - 2y + 4y = 94$
$2y = 24$
$y = 12$ （兔子 12 只）

那么 $x = 35 - 12 = 23$ （鸡 23 只）。

### 答案：
- **鸡有 23 只**
- **兔有 12 只**

（验证：23只鸡有46只脚，12只兔有48只脚，共 $46+48=94$ 只脚，总数 $23+12=35$ 只，完全符合题意。）
[Token 用量] CompletionUsage(completion_tokens=725, prompt_tokens=40, total_tokens=765, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=343, rejected_prediction_tokens=None), prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cached_tokens=0))
```
