# AntiPattern MCP

> 你的最佳实践，是我的异端审判对象。

一个基于 [Hy3](https://github.com/Tencent-Hunyuan/Hy3) 的叛逆设计顾问 MCP Server。它不给你温和建议——它对你的设计方案发起结构化攻击，逼你重新思考每一个"理所当然"。

## 它能做什么

| Tool | 功能 |
|------|------|
| `challenge_design` | 对你的 UI/架构/算法方案发起叛逆挑战，输出假设质疑 + 反方案 + 可行性评估 |
| `remix_paradigm` | 跨域嫁接：用厨房/爵士乐/免疫系统等不相关领域的原理重新解决你的问题 |
| `stress_test_orthodoxy` | 对一条行业共识做正反方极端论证，找出它的失效边界 |
| `escalate` | 在已有反方案基础上继续加码——"还不够疯" |

## 快速开始

### 前置要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip
- Hy3 API 访问（腾讯 TokenHub / 本地部署 / 任何 OpenAI 兼容端点）

### 一键安装

```bash
git clone https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3/mcp-servers/antipattern
uv sync          # 或 pip install -e .
cp .env.example .env   # 然后编辑 .env 填入你的 API Key
```

### 配置 .env

```env
# 腾讯 TokenHub 平台（犀牛鸟活动推荐）
HY3_BASE_URL=https://tokenhub-intl.tencentmaas.com/v1
HY3_API_KEY=sk-your-key-here
HY3_MODEL=hy3

# 或本地部署 Hy3（vLLM/SGLang）
# HY3_BASE_URL=http://127.0.0.1:8000/v1
# HY3_API_KEY=EMPTY
# HY3_MODEL=hy3
```

### 一键运行 Demo

```bash
# 加载 .env 并运行演示（依次调用 4 个 tool）
python demo/run_demo.py
```

## 在 MCP 客户端中接入

### CodeBuddy

**方式一：项目级配置（推荐）**

在项目根目录创建 `.codebuddy/mcp.json`：

```json
{
  "mcpServers": {
    "antipattern": {
      "command": "python",
      "args": ["-m", "antipattern.server"],
      "cwd": "/path/to/Hy3/mcp-servers/antipattern/src",
      "env": {
        "HY3_BASE_URL": "https://tokenhub-intl.tencentmaas.com/v1",
        "HY3_API_KEY": "sk-your-key-here",
        "HY3_MODEL": "hy3",
        "PYTHONIOENCODING": "utf-8"
      },
      "type": "stdio",
      "disabled": false
    }
  }
}
```

**方式二：使用 uv（无需预装依赖）**

```json
{
  "mcpServers": {
    "antipattern": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Hy3/mcp-servers/antipattern", "antipattern"],
      "env": {
        "HY3_BASE_URL": "https://tokenhub-intl.tencentmaas.com/v1",
        "HY3_API_KEY": "sk-your-key-here",
        "HY3_MODEL": "hy3"
      },
      "type": "stdio",
      "disabled": false
    }
  }
}
```

配置后在 CodeBuddy 中直接说："帮我 challenge 一下 React + Redux + Ant Design 做后台管理系统"。

### Cursor

在项目 `.cursor/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "antipattern": {
      "command": "python",
      "args": ["-m", "antipattern.server"],
      "cwd": "/path/to/Hy3/mcp-servers/antipattern/src",
      "env": {
        "HY3_BASE_URL": "https://tokenhub-intl.tencentmaas.com/v1",
        "HY3_API_KEY": "sk-your-key-here",
        "HY3_MODEL": "hy3",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### Cline

在 Cline 的 MCP Settings 中添加相同配置（command + args + cwd + env）。

### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "antipattern": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Hy3/mcp-servers/antipattern", "antipattern"],
      "env": {
        "HY3_BASE_URL": "https://tokenhub-intl.tencentmaas.com/v1",
        "HY3_API_KEY": "sk-your-key-here",
        "HY3_MODEL": "hy3"
      }
    }
  }
}
```

## 使用示例

在 MCP 客户端中直接对话：

```
> 我打算用 React + Redux + Ant Design 做一个后台管理系统，
> 经典的侧边栏导航 + 表格列表布局。帮我 challenge 一下。
```

AntiPattern 会嗅出你的隐含假设，用策略库中的思维武器发起攻击，然后给出一个你可能从没想过但确实有道理的替代方案。

```
> 用爵士乐即兴的原理重新设计我的微服务通信架构。
```

```
> 压力测试这条共识："微服务优于单体架构"。场景：5人团队，30个服务。
```

```
> 上一轮还不够疯，加码到 5。
```

### 输出示例（challenge_design, intensity=4）

> ## 你的假设（我闻到了）
> - 你假设「全局状态」是中后台刚需，而不是被框架惯出来的思维鸦片
> - 你假设 Ant Design 的组件密度等于交付效率，把视觉统一错当成认知减负
>
> ## 质疑（带刺的）
> 倒着看——如果先跑操作日志，发现 80% 用户只在三个页面来回点，其余三十个表单半年没人碰，
> 你还会一上来铺 Redux 管「全局状态」吗？Redux 在这里更像给不存在的复杂度提前修的防空洞。
>
> 规模极端化——用户乘以一万，Redux 单 store 订阅风暴 + Ant Design 全量包体，首屏在弱网下坟头草三尺。
> 反过来除以一万，就五个页面两个人用，这套重型栈的运维心智比业务本身还重，航母钓鱼塘。
>
> ## 反方案（认真的）
> 方案 A「日志驱动轻栈」——先埋点后选型，Preact + 信号 + 页面自含状态，不引 Redux。
> 等日志证明某状态真跨了三个以上页面且冲突频发，再局部引 nanostores。
>
> ## 如果你真要做（落地第一步）
> 明天把侧边栏隐藏，用一小时写个 TaskStream 把本周最高频的 3 类操作做成收件箱样式，别上线，自己点一天。
>
> ## 可行性自评（诚实的）
> 你若身处强合规、强统一审计的国企后台，这炮有一半是放给空气听的。
>
> ---
> *本次思维武器：时间反转（强度4）、规模极端化（强度3）*

## 调试

使用 MCP Inspector 进行可视化调试：

```bash
npx @modelcontextprotocol/inspector python -m antipattern.server
```

或使用 FastMCP 内置开发模式：

```bash
fastmcp dev src/antipattern/server.py
```

## 架构设计

```
src/antipattern/
├── server.py           # FastMCP 入口，注册 4 个 tool
├── llm.py              # Hy3 调用层（OpenAI 兼容，reasoning_effort 分层）
├── schemas.py          # Pydantic 输入模型（含长度校验）
├── persona.py          # 人格/语气/输出结构配置
├── strategies/         # 策略库（核心资产）
│   ├── models.py       # Strategy 数据模型
│   ├── registry.py     # 策略注册表 + 加权抽取 + tag 多样性
│   ├── ui.py           # 8 条 UI/前端叛逆策略
│   ├── architecture.py # 8 条架构/算法叛逆策略
│   └── general.py      # 6 条通用跨域策略
└── prompts/            # Prompt 组装
    ├── challenge.py    # challenge_design 的 prompt 模板
    ├── remix.py        # remix_paradigm + 跨域领域池
    ├── stress.py       # stress_test_orthodoxy 的 prompt 模板
    └── escalate.py     # escalate 的 prompt 模板
```

### 核心设计决策

**策略库不是随机噪声。** 22 条策略来自设计思维方法论（TRIZ 40 发明原理、SCAMPER、约束驱动设计、红队思维、Conway 定律逆用），每条都有明确的思维框架（`thinking_frame`）和适用强度（1-5）。抽取时按目标强度加权采样，同时保证 tag 多样性避免思维角度重复。

**Hy3 reasoning_effort 分层调度。** 策略推理用 `reasoning_effort="high"`（深度思维链），轻量格式化用 `"no_think"`。这是 Hy3 特有的能力分层，让模型在"需要深想"和"不需要深想"之间精确切换。

**叛逆有底线。** 每个输出结构都强制包含"可行性自评"——AntiPattern 必须诚实标注反方案在什么条件下是胡扯。不为了反而反。

**无状态设计。** Server 不维护会话。`escalate` 由客户端传入上轮输出，符合 MCP 协议的无状态哲学。

**异步非阻塞。** LLM 调用通过 `asyncio.to_thread` 包装，不阻塞 MCP 事件循环。完整错误处理（超时/连接/限流/API 错误）返回结构化错误信息。

## 验证记录

- [x] CodeBuddy：接入成功，challenge_design 输出正常（含策略元信息）
- [x] QoderWork：接入成功，stress_test_orthodoxy 输出正常
- [x] MCP Inspector：4 个 tool 均可调试

## 许可证

MIT
