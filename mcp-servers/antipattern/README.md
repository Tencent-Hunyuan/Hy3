# AntiPattern MCP

> 你的最佳实践，是我的异端审判对象。

一个专门唱反调的 MCP Server，跑在 Hy3 上。你给它一个设计方案，它还你一次结构化攻击——不是抬杠，是逼你把"大家都这么做"这句话背后的假设摊开来看。

四个工具：

| Tool | 干什么 |
|------|--------|
| `challenge_design` | 对你的方案发起叛逆挑战。拆假设、给反方案、评可行性 |
| `remix_paradigm` | 跨域嫁接。用厨房/爵士乐/免疫系统的原理重新解你的题 |
| `stress_test_orthodoxy` | 拿一条行业共识做正反方极端论证，找失效边界 |
| `escalate` | 加码。把上一轮输出传进来，它会在上面继续捅 |

## 装

需要 Python 3.10+，推荐用 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3/mcp-servers/antipattern
uv sync          # 或 pip install -e .
cp .env.example .env
```

编辑 `.env`：

```env
# TokenHub（犀牛鸟活动用的）
HY3_BASE_URL=https://tokenhub-intl.tencentmaas.com/v1
HY3_API_KEY=sk-your-key-here
HY3_MODEL=hy3

# 或者本地部署（vLLM/SGLang）
# HY3_BASE_URL=http://127.0.0.1:8000/v1
# HY3_API_KEY=EMPTY
# HY3_MODEL=hy3
```

跑一下确认能用：

```bash
python demo/run_demo.py
```

## 接客户端

所有支持 MCP stdio 的客户端都能接。核心就三个字段：command、args、cwd（或 `--directory`）。

### CodeBuddy

项目根目录 `.codebuddy/mcp.json`：

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

或者用 uv 免装依赖：

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

注意 `mcpServers` 下面直接跟 server 名，别多套一层。

### Cursor / Cline / Claude Desktop

配置结构一样，只是文件位置不同：

- Cursor → `.cursor/mcp.json`
- Cline → MCP Settings 面板
- Claude Desktop → `claude_desktop_config.json`

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

Windows 下如果用 `python -m` 方式启动，env 里加 `"PYTHONIOENCODING": "utf-8"`，不然中文输出会炸。

## 用起来什么样

在客户端里直接说人话：

```
帮我 challenge 一下：React + Redux + Ant Design 做后台管理系统，
经典侧边栏导航 + 表格列表。
```

```
用爵士乐即兴的原理重新设计我的微服务通信架构。
```

```
压力测试这条共识："微服务优于单体架构"。我们5个人，30个服务，没有专职运维。
```

```
上一轮还不够疯，加码到5，方向是彻底推翻从第一性原理来。
```

实际输出长这样（challenge_design, intensity=4）：

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

## 怎么做的

```
src/antipattern/
├── server.py           # FastMCP 入口，4 个 tool
├── llm.py              # Hy3 调用（OpenAI 兼容协议，reasoning_effort 分层）
├── schemas.py          # Pydantic 输入校验
├── persona.py          # 人格、语气、输出结构模板
├── strategies/         # 22 条策略
│   ├── models.py       # Strategy 数据结构
│   ├── registry.py     # 加权采样 + tag 去重
│   ├── ui.py           # 8 条 UI/前端方向
│   ├── architecture.py # 8 条架构/算法方向
│   └── general.py      # 6 条通用跨域
└── prompts/            # 各 tool 的 prompt 组装
    ├── challenge.py
    ├── remix.py        # 含 12 个跨域领域池
    ├── stress.py
    └── escalate.py
```

几个设计决策值得说：

**策略不是随机噪声。** 22 条策略来自 TRIZ 40 发明原理、SCAMPER、约束驱动设计、红队思维、Conway 定律逆用。每条有明确的 `thinking_frame`（思维框架）和适用强度（1-5）。调用时按目标强度加权采样，同时做 tag 多样性约束——不会两次抽到同一个思维角度。

**Hy3 reasoning_effort 分层。** 策略推理走 `reasoning_effort="high"`（完整思维链），轻量格式化走 `"no_think"`。这是 Hy3 的 MoE 架构给的能力——同一个模型，需要深想的时候深想，不需要的时候省算力。

**叛逆有底线。** 每个输出结构都强制带"可行性自评"。AntiPattern 必须说清楚反方案在什么条件下是胡扯。不为反而反——这是 persona 里写死的规矩。

**无状态。** Server 不存会话。`escalate` 的"上一轮输出"由客户端传进来，符合 MCP 的无状态设计。

**异步不阻塞。** LLM 调用走 `asyncio.to_thread`，不卡 MCP 事件循环。超时 120s，max_tokens 4096，错误分类处理（超时/连接/限流/API 错误）返回人话。

## 调试

```bash
npx @modelcontextprotocol/inspector python -m antipattern.server
```

或者 FastMCP 自带的 dev 模式：

```bash
fastmcp dev src/antipattern/server.py
```

## 验证

- CodeBuddy：challenge_design / stress_test_orthodoxy / escalate 均正常
- QoderWork：stress_test_orthodoxy 正常
- MCP Inspector：4 个 tool 全部可调试

## Demo

录屏（CodeBuddy 实际调用，无剪辑）：

- [Demo 1 — challenge_design](https://github.com/zhang66633/Hy3/releases/download/demo-videos/demo-1-challenge.mp4)
- [Demo 2 — stress_test_orthodoxy + escalate](https://github.com/zhang66633/Hy3/releases/download/demo-videos/demo-2-stress-escalate.mp4)
- [Demo 3 — escalate 强度5加码](https://github.com/zhang66633/Hy3/releases/download/demo-videos/demo-3-escalate.mp4)

## License

MIT
