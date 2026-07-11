# Reasoning mode：思考开关对比

启动服务时应配置 reasoning parser：vLLM 使用 `--reasoning-parser hy_v3`，SGLang 使用 `--reasoning-parser hunyuan`。

```bash
python api/examples/05_reasoning_mode/reasoning_mode.py
```

完整请求和解析见 [`reasoning_mode.py`](reasoning_mode.py)。脚本用同一问题依次请求 `no_think` 与 `high`，并解析可选的 `message.reasoning_content`、最终 `message.content`、结束原因、token 用量和耗时。

```python
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1024,
    extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
)
```

推理字段是否单独返回取决于后端和解析器版本，脚本不会假定它一定存在。不要把推理内容直接展示给终端用户或依赖其格式做业务判断。

```text
=== reasoning_effort=no_think ===
id: chatcmpl-e51
model: hy3
role: assistant
reasoning_content: <not returned>
content: 满足条件的最小正整数是 18。
finish_reason: stop
latency: 0.731s
usage: prompt=28, completion=17, total=45

=== reasoning_effort=high ===
id: chatcmpl-e52
model: hy3
role: assistant
reasoning_content: 设该数为 5k+3，逐项检查模 7 的余数……
content: 最小正整数为 18。
finish_reason: stop
latency: 2.408s
usage: prompt=28, completion=96, total=124
```
