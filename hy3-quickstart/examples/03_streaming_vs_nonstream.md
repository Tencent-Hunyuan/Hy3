# 03 · Non-streaming vs Streaming(首 token 时延 / 总耗时)

对比两种模式的延迟特征,帮你选型:交互场景用流式(首字快),批量场景用非流式(整段拿)。可运行脚本:`03_streaming_vs_nonstream.py`。

---

## 请求

同一个问题,只改 `stream`:

```python
import time

Q = "用 80 字介绍腾讯混元 Hy3 模型的特点"

# 非流式
t0 = time.perf_counter()
r = client.chat.completions.create(model="hy3", messages=[{"role":"user","content":Q}])
print(f"非流式 总耗时 {(time.perf_counter()-t0)*1000:.0f} ms")

# 流式 (测首 token)
t0 = time.perf_counter()
stream = client.chat.completions.create(model="hy3", messages=[{"role":"user","content":Q}], stream=True)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(f"流式 首 token (TTFT) {(time.perf_counter()-t0)*1000:.0f} ms")
        break
```

---

## 真实测量结果(同 prompt,同网络)

| 模式 | 首 token (TTFT) | 总耗时 |
|------|----------------|--------|
| **非流式** `stream:false` | 1.59 s | 1.59 s |
| **流式** `stream:true` | **0.67 s** | 1.26 s |

---

## 解读

- **非流式**:服务端生成完整回答后一次性返回。**首字节 ≈ 总耗时**(要等全文生成完)。
- **流式**:边生成边推。**TTFT 仅 0.67 s**,约为非流式的 **42%**;总耗时也略短(首字即可开始渲染)。
- **选型建议**:
  - 聊天 / 实时助手 / 长文 → **流式**(用户秒见首字,体感快 2~3 倍)
  - 结构化提取 / 批处理 / 后台任务 → **非流式**(拿完整 JSON,省去拼接)

> 实测数值受网络与负载影响,以上为代表性量级。TTFT 用 `curl -w "%{time_starttransfer}"` 或脚本计时均可测。
