# 在 Aider 中使用 Hy3

> English: [aider.en.md](aider.en.md) · [返回索引](../README.md)

Aider 是终端中的结对编程 Agent。其官方文档支持任意 OpenAI 兼容端点，模型名需加 `openai/` 前缀。

## 安装与要求

按 [Aider 官方安装说明](https://aider.chat/docs/install.html)使用隔离安装器：

```bash
python -m pip install aider-install
aider-install
aider --version
```

建议使用当前稳定版；以下配置于 2026-07-23 对照 [OpenAI compatible APIs](https://aider.chat/docs/llms/openai-compat.html) 和 [options reference](https://aider.chat/docs/config/options.html) 核对。

## 配置

自建端点：

```bash
export OPENAI_API_BASE=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=EMPTY
aider --model openai/hy3 --edit-format diff
```

OpenRouter 可以直接使用 Aider 的 OpenRouter provider：

```bash
export OPENROUTER_API_KEY='sk-or-v1-...'
aider --model openrouter/tencent/hy3 --edit-format diff
```

`.aider.conf.yml` 可只保存非敏感项：

```yaml
model: openrouter/tencent/hy3
edit-format: diff
auto-commits: false
show-model-warnings: true
```

不要在 YAML 中写 Key。Hy3 是新模型，Aider 可能提示未知价格或元数据；这不等于请求失败，应以实际响应与文件 diff 为准。

## 第一次对话

在一个临时 Git 仓库中运行 Aider，输入：

```text
/ask 只读检查当前仓库，并告诉我你看到了哪些文件；不要修改任何内容。
```

验收：Aider 显示所选模型，返回仓库概览，`git status --short` 仍为空。

## 端到端任务

```text
在 src/slugify.py 实现 slugify(text)，要求支持 Unicode 输入、连续分隔符归一化和空字符串；在 tests/test_slugify.py 用 unittest 覆盖至少 6 个边界条件。完成后运行 python3 -m unittest discover -s tests -v。不要修改其他文件。
```

操作建议：

1. 用 `/add src/slugify.py tests/test_slugify.py` 限定上下文。
2. 审查 Aider 给出的 diff 后再接受。
3. 以真实测试退出码为准，不以“完成”文本为准。
4. 用 `/undo` 可撤销本轮修改；本指南关闭 `auto-commits`，避免产生未授权提交。

最终可让 Aider对本仓库 `issue2/demo/` 做同类改动，并运行统一验收命令。页面结果示例：

![Evidence Board 离线运行截图](../../assets/evidence-board-offline.png)

## 常见问题

| 症状 | 处理 |
|:---|:---|
| `Unknown model` 警告 | 保留 `openai/` 或 `openrouter/` 前缀；必要时显式指定 `--edit-format diff` |
| 连接自建端点失败 | `OPENAI_API_BASE` 必须包含 `/v1`；确认服务监听地址 |
| Key 泄露到 shell history | 通过安全的环境注入或 `.env`（加入 `.gitignore`）提供，不写在命令参数中 |
| Aider 修改范围过大 | 只 `/add` 必要文件，并在 prompt 明确禁止修改其他路径 |
| 推理参数被忽略 | Aider 的 `--reasoning-effort` 是 OpenAI 风格字段；自建 Hy3 的 `chat_template_kwargs` 未必能由该开关表达，先验证实际服务日志 |
