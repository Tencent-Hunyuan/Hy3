# 05 · Reasoning Mode

## 说明

对比 `reasoning_effort=no_think` 与 `high` 的输出差异。

## 运行

```bash
python 05_reasoning_mode.py
```

## 请求

本地（对齐仓库 README）：

```python
extra_body = {
    "chat_template_kwargs": {
        "reasoning_effort": "no_think"  # 或 "low" / "high"
    }
}
```

`05_reasoning_mode.py` 同时附带兼容字段，便于不同网关使用。

## 响应字段

- `message.content`：最终回答
- `message.reasoning_content`：思考过程（若平台返回）

## 示例输出

环境：腾讯云 TokenHub。

```text
=== reasoning_effort=no_think ===
content: **答案：至少 8 人两门都喜欢。**

**简要推理：**
班级总人数为 30 人。
喜欢数学的有 18 人，喜欢英语的有 20 人。
如果不考虑重叠，喜欢至少一门的人数最多为 18 + 20 = 38 人。
但班级只有 30 人，所以多出来的部分就是两门都喜欢的最少人数：
18 + 20 - 30 = 8
因此，至少有 8 人两门都喜欢。
reasoning_content: None

=== reasoning_effort=high ===
content: **答案：至少有 8 人两门都喜欢。**

**简要推理：**
根据集合的容斥原理，喜欢数学或英语的人数 = 喜欢数学的人数 + 喜欢英语的人数 - 两门都喜欢的人数。
因为喜欢数学或英语的人数最多只能是全班人数 30 人，所以 18 + 20 - 两门都喜欢的人数 ≤ 30，得出两门都喜欢的人数 ≥ 8。
reasoning_content: 这是一个典型的集合容斥原理问题。
设班级总人数 N = 30，喜欢数学 |M| = 18，喜欢英语 |E| = 20，两门都喜欢 |M ∩ E| = x。
至少喜欢一门 |M ∪ E| = 18 + 20 - x = 38 - x。
因 |M ∪ E| ≤ 30，故 38 - x ≤ 30，即 x ≥ 8。
当 x = 8 时，只喜欢数学 10 人、只喜欢英语 12 人、两门都喜欢 8 人，合计 30，情形可行。
若 x = 7，则并集为 31，超过总人数，不可能。
因此至少有 8 人两门都喜欢。
```
