# 05 · Reasoning Mode(思考过程 开/关 对比)

Hy3 支持**交错式思考(Interleaved Thinking)**:推理时在 `reasoning_content` 字段产出思考过程,正文 `content` 给最终答案。用 `reasoning_effort` 控制思考深度。

> OpenAI SDK 未声明 `reasoning_effort`,Python 里用 `extra_body` 透传。可运行脚本:`05_reasoning_mode.py`。

---

## 对比:简单问题 vs 推理题

### 简单问题(无需推理)

```json
{"role": "user", "content": "你好"}
```

响应里 **没有** `reasoning_content`,`reasoning_tokens = 0`:

```json
"usage": {
  "completion_tokens_details": { "reasoning_tokens": 0 }
}
```

### 推理题 + `reasoning_effort: high`

```python
resp = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content":
        "房间里有3个开关控制隔壁3盏灯,你只能进隔壁看一次,如何分辨每个开关对应哪盏灯?"}],
    max_tokens=4000,
    extra_body={"reasoning_effort": "high"},   # 透传思考强度
)
m = resp.choices[0].message
print(m.reasoning_content)   # 思考过程
print(m.content)             # 最终答案
```

### 真实响应(节选)

`message` 同时含 `role / content / reasoning_content` 三个字段:

```
keys in message: ['role', 'content', 'reasoning_content']

reasoning_content (思考, 前300字):
  This is a classic logic puzzle.
  The setup:
  - Room A has 3 switches (Switch 1/2/3).
  - Room B has 3 light bulbs.
  - You can only go into Room B *once*.
  ...

content (最终答案, 前300字):
  这是一个经典的逻辑推理题,核心思路是利用灯泡发光时会发热的物理特性(温度)来增加判断维度。
  1. 先打开第1个开关几分钟(使灯泡发热),再关掉,打开第2个开关,第3个保持关闭。
  2. 进房间看一次:亮着→第2个开关;不亮但发热→第1个;不亮且凉→第3个。
```

---

## 解读与用法

| 场景 | 建议 |
|------|------|
| 闲聊 / 翻译 / 简单 QA | 默认即可(不思考,`reasoning_tokens=0`,快且省) |
| 数学 / 逻辑 / 代码 / 多步规划 | `reasoning_effort="high"`(深度思考,答案更可靠,耗时与 token 上升) |
| 介于两者之间 | `reasoning_effort="low"`(轻量思考) |

**要点**:
- 思考过程在 **`reasoning_content`**(流式时为每个 chunk 的 `delta.reasoning_content`),与正文 `content` **分开**,前端可选择性展示(如「展开思考」)。
- `usage.completion_tokens_details.reasoning_tokens` 单独计思考 token,便于核算成本。
- 推理时 Hy3 的思考常以**英文**进行,但最终 `content` 会用**用户语言**回答——这是正常现象。

> `reasoning_effort` 取值与各取值下 token/耗时差异,可用 `05_reasoning_mode.py` 自行跑对比(以你账号实际为准)。
