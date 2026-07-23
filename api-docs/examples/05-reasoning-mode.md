# Example 05: Reasoning Mode

对比 Hy3 **思考模式开启**（`reasoning_effort="high"`）与**关闭**（`reasoning_effort="no_think"`）的输出差异。

---

## 背景

Hy3 是"快慢思考融合"模型：

- **快思考**（`no_think`）：直接生成回复，适合简单对话
- **慢思考**（`high`）：先进行深度思维链推理，再给出最终答案，适合数学、编程、逻辑推理

---

## 环境准备

```bash
pip install openai
```

---

## 对比实验：数学证明题

### 完整代码

```python
import os
import time
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

PROMPT = "证明：在任意 6 个人中，要么存在 3 个人两两认识，要么存在 3 个人两两不认识。"


# ============================================================
# 测试 1: 关闭思考模式
# ============================================================
def test_no_think():
    print("=" * 60)
    print("【reasoning_effort = no_think】")
    print("=" * 60)

    start = time.time()
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        max_tokens=1024,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )
    elapsed = time.time() - start

    content = response.choices[0].message.content
    usage = response.usage

    print(f"  耗时:              {elapsed:.2f}s")
    print(f"  prompt_tokens:     {usage.prompt_tokens}")
    print(f"  completion_tokens: {usage.completion_tokens}")
    print(f"  total_tokens:      {usage.total_tokens}")
    print(f"  finish_reason:     {response.choices[0].finish_reason}")
    print(f"\n--- 回复内容 ---\n{content}\n")

    return {"mode": "no_think", "elapsed": elapsed, "usage": usage, "content": content}


# ============================================================
# 测试 2: 开启深度思考模式
# ============================================================
def test_high_think():
    print("=" * 60)
    print("【reasoning_effort = high】")
    print("=" * 60)

    start = time.time()
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        max_tokens=2048,  # 深度思考需要更大 token 预算
        extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
    )
    elapsed = time.time() - start

    content = response.choices[0].message.content
    usage = response.usage

    print(f"  耗时:              {elapsed:.2f}s")
    print(f"  prompt_tokens:     {usage.prompt_tokens}")
    print(f"  completion_tokens: {usage.completion_tokens}")
    print(f"  total_tokens:      {usage.total_tokens}")
    print(f"  finish_reason:     {response.choices[0].finish_reason}")
    print(f"\n--- 回复内容 ---\n{content}\n")

    return {"mode": "high", "elapsed": elapsed, "usage": usage, "content": content}


# ============================================================
# 执行对比
# ============================================================
if __name__ == "__main__":
    r1 = test_no_think()
    r2 = test_high_think()

    print("=" * 60)
    print("【对比汇总】")
    print("=" * 60)
    print(f"  {'指标':<25s} {'no_think':>12s} {'high':>12s}")
    print(f"  {'-'*45}")
    print(f"  {'耗时':<25s} {r1['elapsed']:>11.2f}s {r2['elapsed']:>11.2f}s")
    print(f"  {'completion_tokens':<25s} {r1['usage'].completion_tokens:>12d} {r2['usage'].completion_tokens:>12d}")
    print(f"  {'total_tokens':<25s} {r1['usage'].total_tokens:>12d} {r2['usage'].total_tokens:>12d}")
    print(f"  {'回复长度(字符)':<25s} {len(r1['content']):>12d} {len(r2['content']):>12d}")
    print()

    print("💡 观察：")
    print("  - 思考模式通常消耗更多 completion_tokens（含思考过程）")
    print("  - 耗时更久（推理步数增加）")
    print("  - 回复质量更高、推理更严谨")
    print("  - 适合复杂数学/逻辑/编程任务")
```

### 示例输出

```
============================================================
【reasoning_effort = no_think】
============================================================
  耗时:              6.66s
  prompt_tokens:     44
  completion_tokens: 473
  total_tokens:      517
  finish_reason:     stop

--- 回复内容 ---
这是一个经典的图论/组合数学问题，通常称为 **拉姆齐数 \(R(3,3)=6\)** 的定理。下面给出简洁而严谨的证明。

---

### 1. 建模
将 6 个人看作图 \(G\) 的 6 个顶点。

- 若两人**认识**，就在对应顶点之间连一条**红边**；
- 若两人**不认识**，就连一条**蓝边**。

于是得到的是一个**完全图 \(K_6\)**，每条边不是红就是蓝。

我们要证明：
> 图中要么存在一个**红色三角形**（3 人两两认识），要么存在一个**蓝色三角形**（3 人两两不认识）。

---

### 2. 任取一人分析
从 6 个人中任取一人，记为 \(A\)。

\(A\) 与其余 5 个人都有一条边（红或蓝），因此：

- \(A\) 发出的 5 条边中，
- 根据抽屉原理，至少有  
  \[
  \left\lceil \frac{5}{2} \right\rceil = 3
  \]
  条是**同色**的。

不妨设 \(A\) 与 \(B,C,D\) 三人之间的边都是**红色**（蓝色情况完全对称）。

---

### 3. 分情况讨论

#### 情况一：\(B,C,D\) 中至少有两条红边
例如 \(B\) 与 \(C\) 认识（红边），那么：
- \(A-B\) 红
- \(A-C\) 红
- \(B-C\) 红

得到红色三角形 \(ABC\)，即存在 3 人两两认识。

#### 情况二：\(B,C,D\) 之间全为蓝边
那么 \(B,C,D\) 三人两两不认识，构成蓝色三角形，即存在 3 人两两不认识。

---

### 4. 结论
无论哪种情况，都必然出现：
- 3 人两两认识，或
- 3 人两两不认识。

因此，在任意 6 个人中，上述两种情形至少有一种成立。

\[
\boxed{R(3,3)=6}
\]

证毕。

============================================================
【reasoning_effort = high】
============================================================
  耗时:              7.91s
  prompt_tokens:     44
  completion_tokens: 580
  total_tokens:      624
  finish_reason:     stop

--- 回复内容 ---
这是一个经典的图论问题，通常称为 **拉姆齐数 \(R(3,3)=6\)** 的证明。下面给出简洁而严谨的证明。

---

### 1. 模型化

把 6 个人看成图的 6 个顶点。  
任意两个人之间，若**认识**，连一条红边；若**不认识**，连一条蓝边。  
于是对任意两个顶点，恰好有一条红边或一条蓝边。

我们要证明：  
图中要么存在一个**红色三角形**（3 人两两认识），要么存在一个**蓝色三角形**（3 人两两不认识）。

---

### 2. 任取一个人分析

设这 6 个人中有一个人记为 \(A\)。

\(A\) 与其余 5 个人都有边相连，因此这 5 条边中：

- 红色边（认识的人）
- 蓝色边（不认识的人）

由抽屉原理，5 条边分到两种颜色中，至少有一种颜色不少于 3 条。

即以下两种情况必居其一：

1. \(A\) 至少认识其中 3 个人；
2. \(A\) 至少不认识其中 3 个人。

---

### 3. 情况一：\(A\) 认识至少 3 个人

设 \(A\) 认识的三个人为 \(B,C,D\)，即边 \(AB,AC,AD\) 都是红色。

考察 \(B,C,D\) 三人之间的关系：

- 若 \(B,C,D\) 中有任意两人互相认识（例如 \(B,C\) 红边），  
  则 \(A,B,C\) 构成三角形且三边皆红，即存在 3 人两两认识。
- 若 \(B,C,D\) 中任意两人都不认识，  
  则 \(B,C,D\) 三边皆蓝，即存在 3 人两两不认识。

---

### 4. 情况二：\(A\) 不认识至少 3 个人

设 \(A\) 不认识的三个人为 \(B,C,D\)，即边 \(AB,AC,AD\) 都是蓝色。

同理考察 \(B,C,D\)：

- 若其中任意两人不认识（蓝边），则与 \(A\) 构成蓝色三角形，存在 3 人两两不认识；
- 若其中任意两人都认识（全为红边），则 \(B,C,D\) 构成红色三角形，存在 3 人两两认识。

---

### 5. 结论

无论哪种情况，都必然出现：

- 3 个人两两认识，或
- 3 个人两两不认识。

因此在任意 6 个人中，上述结论恒成立。

\[
\boxed{R(3,3)=6}
\]

证毕。

============================================================
【对比汇总】
============================================================
  指标                            no_think         high
  ---------------------------------------------
  耗时                               6.66s        7.91s
  completion_tokens                  473          580
  total_tokens                       517          624
  回复长度(字符)                           805          975

💡 观察：
  - 思考模式通常消耗更多 completion_tokens（含思考过程）
  - 耗时更久（推理步数增加）
  - 回复质量更高、推理更严谨
  - 适合复杂数学/逻辑/编程任务

```