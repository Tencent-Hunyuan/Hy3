# 05 思考模式

对比 Chat Completions API 普通模式和推理模式的响应。

## 运行

```bash
uv run --env-file .env python examples/05_reasoning_mode.py
```

## 请求和解析

脚本使用相同问题分别发起普通请求和带 `reasoning_effort: "high"` 的请求，并从 `message.content` 读取两次结果，再打印推理请求的 `usage`。

## 输出示例

```text
普通模式：
我们计算 \( 37 \times 24 \)：

**方法一：直接分解**
\[
37 \times 24 = 37 \times (20 + 4) = 37 \times 20 + 37 \times 4
\]
\[
37 \times 20 = 740
\]
\[
37 \times 4 = 148
\]
\[
740 + 148 = 888
\]

**方法二：列竖式**
\[
\begin{array}{c}
\phantom{0}37\\
\times\phantom{0}24\\\hline
\phantom{0}148\ \ (37\times4)\\
+740\ \ (37\times20)\\\hline
\phantom{0}888
\end{array}
\]

**结果：**
\[
37 \times 24 = 888
\]

**简要说明：**  
37 乘以 24 等于 888，这是一个三位数，计算过程可以通过分配律或竖式完成，结果正确无误。

推理模式：
计算结果为：**37 × 24 = 888**

**简要说明：**
可以将 24 拆分为 20 + 4，利用分配律计算：
- 37 × 20 = 740
- 37 × 4 = 148
- 740 + 148 = 888

结果 888 是一个三位数，且三个数位上的数字相同（均为 8）。

推理模式 usage：
CompletionUsage(completion_tokens=311, prompt_tokens=24, total_tokens=335, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=232, rejected_prediction_tokens=None), prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cache_write_tokens=None, cached_tokens=0))
```

推理字段和可用取值取决于模型及 TokenHub 服务端支持范围，不应展示模型的内部思维过程。
