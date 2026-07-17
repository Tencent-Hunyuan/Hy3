# 在 Codex CLI 中使用 Hy3

> 🌐 English version: [codex-cli.en.md](codex-cli.en.md)

## 工具简介

[Codex CLI](https://github.com/openai/codex) 是 OpenAI 开源的终端 AI 编程工具，支持在命令行中通过自然语言完成代码生成、调试、重构等任务。它基于 OpenAI Agents SDK，**支持接入任何 OpenAI 兼容 API**，因此可以配置 Hy3 作为后端模型。

## 适用场景

- 终端原生 AI 编程体验
- 自动化脚本生成与批量文件处理
- CI/CD 流水线中的 AI 驱动步骤
- 不需要 IDE 的轻量编程环境

## 版本要求

| 项 | 要求 |
|:---|:---|
| Node.js | ≥ 18 |
| Codex CLI | `npm install -g @openai/codex` |
| Hy3 服务 | 自建 OpenAI 兼容 API 端点 |
| 终端 | macOS / Linux Terminal 或 Windows PowerShell / WSL |

## 配置项

### 环境变量配置

```bash
# 配置 Hy3 端点
export OPENAI_BASE_URL="https://tokenhub.tencentmaas.com/v1"
export OPENAI_API_KEY="your-api-key"
export CODEX_MODEL="hy3"

# 可选：设置推理参数
export CODEX_TEMPERATURE="0.9"
export CODEX_MAX_TOKENS="8192"
```

### 写入配置文件（推荐）

先设置环境变量，codex不允许直接使用环境变量

setx HY3_API_KEY "your-api-key"

在 `~/.codex/config.json`（或项目根目录 `.codex.yaml`）中：

```
model = "hy3"
model_provider = "hy3-tokenhub"

[model_providers.hy3-tokenhub]
name = "Tencent Hy3"
base_url = "https://tokenhub.tencentmaas.com/v1"
env_key = "HY3_API_KEY"
max_tokens = 262144
supports_tools = true
timeout = 180
```

## 端到端 Demo

### Demo 1：一行命令生成整个网页

```bash
codex "创建一个单文件 HTML 页面：精美的个人名片，包含头像、姓名、职位、社交链接，使用纯 CSS 动画"
```

**Hy3 输出**：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>个人名片</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        .card {
            background: rgba(255,255,255,0.95); border-radius: 20px;
            padding: 40px; text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: float 3s ease-in-out infinite;
            max-width: 360px; width: 90%;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        .avatar {
            width: 100px; height: 100px; border-radius: 50%;
            margin: 0 auto 20px; background: linear-gradient(135deg, #f093fb, #f5576c);
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 40px; font-weight: bold;
        }
        .name { font-size: 24px; font-weight: 700; color: #333; margin-bottom: 4px; }
        .title { color: #666; font-size: 14px; margin-bottom: 20px; }
        .bio { color: #555; font-size: 13px; line-height: 1.6; margin-bottom: 24px; }
        .links { display: flex; justify-content: center; gap: 16px; }
        .links a {
            display: inline-flex; align-items: center; justify-content: center;
            width: 40px; height: 40px; border-radius: 50%;
            background: #f0f0f0; color: #555; text-decoration: none;
            font-size: 18px; transition: all 0.3s ease;
        }
        .links a:hover { background: #667eea; color: white; transform: scale(1.1); }
    </style>
</head>
<body>
    <div class="card">
        <div class="avatar">张</div>
        <div class="name">张三</div>
        <div class="title">全栈工程师 · 开源爱好者</div>
        <p class="bio">热爱技术，专注 Web 开发与 AI 应用。<br>GitHub 活跃贡献者，技术博客作者。</p>
        <div class="links">
            <a href="#" title="GitHub">⌨</a>
            <a href="#" title="Twitter">𝕏</a>
            <a href="#" title="LinkedIn">in</a>
            <a href="#" title="Email">✉</a>
        </div>
    </div>
</body>
</html>
```

### Demo 2：交互式重构

```bash
# 启动 Codex 交互模式
codex --model hy3

# 在交互模式中：
> 读取 src/utils.py，把里面的同步 IO 改成 asyncio 风格
> 为上面改动的函数添加类型注解和 docstring
> 在 tests/ 下生成对应的 pytest 测试用例
```

### Demo 3：批量文件操作

```bash
codex "读取 src/ 下所有 .ts 文件，找出使用了 any 类型的代码，逐一替换为明确的类型定义"
```

## 常见注意事项

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| `Error: Model not found` | 模型名配置错误 | 确认使用 `hy3`（自建）或 `tencent/hy3`（OpenRouter） |
| 输出被截断 | `max_tokens` 默认值太小 | 修改 `~/.codex/config.json` 中的 `maxTokens` |
| `reasoning_effort` 不生效 | Codex CLI 默认不传递自定义参数 | 通过 `--extra-body` 传递或修改 Codex 源码 |
| 路径不正确 | Codex 在错误的目录执行 | `cd` 到项目根目录后再运行 |
| 编辑模式不工作 | 文件权限问题 | 确认文件可读写，Codex 在交互模式下有确认步骤 |


[← 返回索引](../README.md)
