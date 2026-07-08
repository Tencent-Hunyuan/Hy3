# Hy3 with Aider

[Aider](https://aider.chat/) 是终端下的 AI 编程助手，支持任意 OpenAI 兼容 API。

## 1. 安装与版本要求

- Python ≥ 3.9
- `aider-chat`（已验证版本 **0.86.2**）

```bash
pip install aider-chat
```

- 本地或云端已部署 Hy3 服务

## 2. 配置项

| 配置项 | 值 |
|--------|-----|
| 协议 | OpenAI 兼容 |
| Base URL | `http://127.0.0.1:8000/v1`（本地） |
| API Key | `EMPTY`（本地） |
| Model 名 | `openai/hy3`（格式固定 `openai/<model>`） |
| 配置入口 | 环境变量 或 `~/.aider.conf.yml`（本机已配置） |

## 3. 端到端流程

### 步骤 1：配置

方式一：环境变量

```bash
export OPENAI_API_BASE=http://127.0.0.1:8000/v1
export OPENAI_API_KEY=EMPTY
export AIDER_MODEL=openai/hy3
```

方式二：`~/.aider.conf.yml`（本机已写入）

```yaml
openai-api-base: http://127.0.0.1:8000/v1
openai-api-key: EMPTY
model: openai/hy3
```

### 步骤 2：第一次对话

```bash
cd /tmp/demo && aider
# 启动后输入：
> 你好，简单介绍一下你自己
```

返回 Hy3 回复即连接成功。

### 步骤 3：跑通一个真实任务

```
> 给当前目录下的 main.py 添加类型注解和 docstring，
> 并用 pytest 写两个单元测试验证 add 函数。
```

Aider 调用 Hy3 编辑文件并自动运行测试。

常用参数：`--edit-format diff`、`--no-auto-commits`、`--yes`。

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南 #6](../../screenshots/README.md#6-aider-终端)
> - 图 1：aider 启动与模型识别
> - 图 2：第一次对话
> - 图 3：真实任务（编辑文件 + 跑测试）

## 5. 常见注意事项

- Aider 依赖 tool calling 做文件编辑，Hy3 需启用 `--enable-auto-tool-choice`
- 编辑失败可尝试 `--edit-format diff`
- `--model` 必须是 `openai/<model_name>` 格式
- 建议配合 Git 使用，便于查看 diff
- 远程/SSH 开发需保证 Hy3 端口可达
