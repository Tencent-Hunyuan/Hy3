# 03 · Non-stream vs Stream

## 说明

同一 prompt 下对比非流式与流式时延。

- **非流式**：一次返回完整结果
- **流式**：记录首 token 时延（TTFT）与总耗时

## 运行

```bash
python 03_nonstream_vs_stream.py
```

## 指标

| 指标 | 非流式 | 流式 |
|------|--------|------|
| TTFT | 记为总耗时（首包即全文） | 第一个非空 `delta.content` 到达时间 |
| total | 完整响应返回时间 | 流结束时间 |

实际数值受网络与负载影响。

## 示例输出

```text
=== non-stream ===
{'mode': 'non-stream', 'ttft_s': 3.193050599991693, 'total_s': 3.193050599991693, 'chars': 35, 'preview': '源码公开聚群贤，\n众手添薪火始燃。\n无界共享通大道，\n春风吹绿万重山。'}
=== stream ===
{'mode': 'stream', 'ttft_s': 0.9790744999918388, 'total_s': 1.7011559999955352, 'chars': 35, 'preview': '代码如光破闭锁，\n众手同耕无界河。\n源码摊开星海阔，\n千秋智慧共磋磨。'}

说明: non-stream 的 ttft_s 记为总耗时（首包即完整响应）；stream 的 ttft_s 为第一个 content chunk 到达时间。
```
