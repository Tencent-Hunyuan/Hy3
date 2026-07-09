# 03 非流式 vs 流式延迟对比示例

## 简介

本示例对**同一个 prompt** 分别以非流式与流式两种方式调用 Hy3，
使用 `time.perf_counter()` 高精度计时，对比两类关键延迟指标：

- **非流式**：一次性等待模型生成完整结果后返回，主要测量**总耗时**。
- **流式**：模型边生成边推送 chunk，测量两个指标：
  - **TTFT（Time To First Token，首 token 延迟）**：从发起请求到收到第一个非空 `delta.content` 的时间。
  - **总耗时**：从发起请求到流式迭代结束（收到最后一个 chunk）的时间。

通过对比可以直观看到：流式调用的 **TTFT 远小于非流式总耗时**，因此更适合交互式场景；
而非流式调用在**批量处理 / 后处理**场景下更简单直接。

---

## 完整请求

> 运行前请先通过 vLLM / SGLang 部署 Hy3 服务（默认监听 `127.0.0.1:8000`）。
> 可通过环境变量 `HY3_BASE_URL`、`HY3_API_KEY` 覆盖连接信息。
> 完整可运行脚本位于 `../en/03_nonstream_vs_stream.py`。

```python
"""
Hy3 非流式 vs 流式延迟对比示例 (examples/en/03_nonstream_vs_stream.py)

对同一个 prompt 分别以非流式和流式方式调用 Hy3，
使用 time.perf_counter() 测量：
    - 非流式：总耗时（等待完整生成返回）
    - 流式：首 token 延迟（TTFT，首个非空 delta.content 到达时间）与总耗时

运行前请先通过 vLLM / SGLang 部署 Hy3 服务（默认监听 127.0.0.1:8000）。
可通过环境变量覆盖连接信息：
    HY3_BASE_URL  服务地址（默认 http://127.0.0.1:8000/v1）
    HY3_API_KEY   API Key（本地部署任意值均可，默认 EMPTY）
"""

import os
import time

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

# 固定的对比 prompt
messages = [
    {
        "role": "user",
        "content": (
            "请用中文简要介绍混合专家模型（MoE）的工作原理，"
            "并举一个生活中的类比，回答约 150 字。"
        ),
    },
]

common_kwargs = dict(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

# ---------- 非流式 ----------
print("=== 非流式调用 ===")
t0 = time.perf_counter()
response = client.chat.completions.create(**common_kwargs, stream=False)
t1 = time.perf_counter()
nonstream_total = t1 - t0
nonstream_text = response.choices[0].message.content
print(f"响应内容:\n{nonstream_text}")
print(f"\n非流式总耗时: {nonstream_total:.3f} s\n")

# ---------- 流式 ----------
print("=== 流式调用 ===")
t0 = time.perf_counter()
stream = client.chat.completions.create(**common_kwargs, stream=True)
ttft = None
parts = []
for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = delta.content
    if content:  # 首个非空 token
        if ttft is None:
            ttft = time.perf_counter() - t0
        parts.append(content)
t1 = time.perf_counter()
stream_total = t1 - t0
stream_text = "".join(parts)
print(f"响应内容:\n{stream_text}")
print(f"\n流式首 token 延迟 (TTFT): {ttft:.3f} s")
print(f"流式总耗时: {stream_total:.3f} s\n")

# ---------- 对比汇总 ----------
print("=== 对比汇总 ===")
print(f"非流式总耗时:           {nonstream_total:.3f} s")
print(f"流式  TTFT:             {ttft:.3f} s")
print(f"流式  总耗时:           {stream_total:.3f} s")
if ttft is not None:
    print(f"TTFT / 非流式总耗时:    {ttft / nonstream_total:.1%}")
```

---

## 完整 response 解析

### 1. 非流式响应（`stream=False`）

非流式调用会**阻塞**直到模型生成完整个回答，然后一次性返回一个完整的 `ChatCompletion` 对象：

```python
response = client.chat.completions.create(**common_kwargs, stream=False)
# response.choices[0].message.content 即为完整文本
```

- **计时方式**：在调用前记录 `t0 = time.perf_counter()`，调用返回后记录 `t1`，
  `非流式总耗时 = t1 - t0`。这段时间 = 网络往返 + 模型生成全部 token 的时间。
- 文本可直接从 `response.choices[0].message.content` 一次性读取，无需拼接。
- `response.usage` 通常有值，可直接获取 token 用量。

### 2. 流式响应（`stream=True`）

流式调用立即返回一个迭代器，模型边生成边推送 `ChatCompletionChunk`：

```python
stream = client.chat.completions.create(**common_kwargs, stream=True)
```

- **TTFT（首 token 延迟）测量**：
  - 在发起调用前记录 `t0 = time.perf_counter()`。
  - 遍历 chunk，当遇到第一个**非空** `delta.content` 时，
    `TTFT = time.perf_counter() - t0`，并停止更新 TTFT（用 `if ttft is None` 保证只记录一次）。
  - 注意要跳过 `delta.content` 为 `None` 或 `""` 的 chunk（例如只携带 `role` 的首帧）。
- **总耗时测量**：流迭代结束后记录 `t1`，`流式总耗时 = t1 - t0`，包含 TTFT + 后续所有 token 的生成与传输时间。
- 文本需自行用 `"".join(parts)` 拼接得到完整内容。
- 默认 `chunk.usage` 为 `None`；如需用量可传 `stream_options={"include_usage": True}`。

### 3. 两者的关系

- 在生成内容相同的情况下，**流式总耗时 ≈ 非流式总耗时**（生成工作量相当，差异主要来自分块传输与网络）。
- 关键差异在于**首字时间**：非流式下用户需等待 `总耗时` 才能看到任何内容；
  流式下用户在 `TTFT`（通常远小于总耗时）后即可看到首个字，体感更流畅。
- 比值 `TTFT / 非流式总耗时` 反映了“用户需要等待的比例”，是交互体验的重要指标。

### 4. 何时使用哪种模式

| 模式 | 优点 | 适用场景 |
|:---|:---|:---|
| 非流式 | 一次性拿到完整结果，代码简单，`usage` 直接可用 | 批量推理、后处理、结构化抽取、需要完整文本再做下游处理 |
| 流式 | TTFT 低，可边生成边展示，体感流畅 | 聊天助手、交互式问答、实时写作、终端打字机效果 |

> 计时建议使用 `time.perf_counter()` 而非 `time.time()`：前者为高精度单调时钟，适合测量短时间间隔，不受系统时间回拨影响。

---

## 示例输出

> 以下为**示例输出**（代表性数据，非真实运行结果），实际数值取决于硬件、负载、生成长度等因素。

```
=== 非流式调用 ===
响应内容:
混合专家模型（MoE）通过门控网络为每个 token 动态选择少量“专家”子网络进行计算，从而在扩大总参数量的同时保持较低的激活参数量与推理成本。生活中可以类比为医院分诊：患者（token）进入后，分诊台（门控）根据症状把它分配给最合适的几位专科医生（专家）诊治，而不是让所有医生都同时参与。

非流式总耗时: 3.842 s

=== 流式调用 ===
响应内容:
混合专家模型（MoE）通过门控网络为每个 token 动态选择少量“专家”子网络进行计算，从而在扩大总参数量的同时保持较低的激活参数量与推理成本。生活中可以类比为医院分诊：患者（token）进入后，分诊台（门控）根据症状把它分配给最合适的几位专科医生（专家）诊治，而不是让所有医生都同时参与。

流式首 token 延迟 (TTFT): 0.237 s
流式总耗时: 3.798 s

=== 对比汇总 ===
非流式总耗时:           3.842 s
流式  TTFT:             0.237 s
流式  总耗时:           3.798 s
TTFT / 非流式总耗时:    6.2%
```

可以看到：两种模式的**总耗时接近**（生成长度相同），但流式的 **TTFT（0.237 s）远小于非流式总耗时（3.842 s）**，
用户在约 0.24 秒后即可看到第一个字，而非流式需要等待近 3.8 秒才能看到任何输出——这正是流式调用在交互场景下的核心价值。
