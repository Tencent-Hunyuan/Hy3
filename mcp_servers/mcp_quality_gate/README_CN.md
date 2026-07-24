# Hy3 MCP 质量门禁

[English](README.md) | [简体中文](README_CN.md)

> 交付状态：规划的 8 个阶段均已完成。TypeScript stdio Server、4 个公开工具、
> 目标注册表、有界协议检查、确定性与可选 Hy3 审计、兼容性比较、安全探针生成、
> 可复现评测、干净包验证、双语文档和双客户端证据均已包含在仓库中。

Hy3 MCP 质量门禁是一个本地 stdio MCP Server，用来检查其他预先注册的本地
MCP Server。它把确定性的协议与 JSON Schema 检查和 Hy3 语义审查结合起来，
输出带证据的问题、可复现分数、兼容性报告以及不会被自动执行的测试用例。

## “质量门禁”到底是什么

这里的“门禁”借用了现实世界门禁的比喻，但它不是控制门锁、门卡或楼宇入口的
实体设备。它也不是网络防火墙、入侵检测系统、杀毒软件或运行时沙箱。

它更像 CI/CD 流程中的**发布前检查点**。一个 MCP Server 准备接入客户端或
发布新版本时，先经过这道检查：

```text
预先注册的本地 MCP Server
          |
          v
协议握手和 tools/list 确定性检查
          |
          v
JSON Schema、说明文档和安全注解审计
          |
          v
可选的 Hy3 语义审查
          |
          v
分数 + 证据位置 + 修复建议 + 兼容性结论
```

确定性代码负责回答“协议是否合法、Schema 是否成立、进程是否超时”等可复现
事实。Hy3 负责回答“说明是否含糊、工具是否重叠、安全表述是否误导、迁移影响
是否清楚”等语义问题。两类结果始终分开：

- Hy3 的意见不会伪装成协议事实；
- Hy3 结果必须通过本地严格 Schema 验证；
- 每条问题必须指向协议事件、工具名或 JSON Pointer；
- 数字评分只由确定性规则改变；
- Hy3 不可把确定性的 breaking 结论降级；
- 目标描述、stderr 和模型输出全部按不可信数据处理。

初始版本只启动目标、完成 MCP 初始化并读取工具合约。它不会调用目标的业务工具，
不会执行生成的探针，也不会接受 MCP 调用者传入的任意命令。因此它是发布前的
合约质量检查，而不是对目标运行时绝对安全的证明。

## 为什么需要它

MCP Server 即使语法正确，也可能让 Agent 难以正确、安全地使用，例如：

- 工具说明含糊，输入、输出、副作用或失败方式没有写清；
- 参数 Schema 缺少约束，或 required、enum、类型定义互相矛盾；
- 安全注解与工具实际描述冲突；
- 新版本删除工具、增加必填参数或收窄输出，造成兼容性破坏；
- stdout 混入启动日志，破坏 JSON-RPC；
- 启动、响应或输出没有上限；
- 多个工具意图高度重叠，模型难以选择。

协议检查器擅长找确定性错误，语言模型擅长理解语义。质量门禁把两者放在受控边界
内，并要求所有结论都能回到证据。

## 4 个公开工具

| 工具 | 作用 | Hy3 的角色 |
| --- | --- | --- |
| `mcpq_inspect_server` | 启动已注册目标，协商 MCP，读取工具并验证声明合约。 | 通过/失败由确定性代码决定。 |
| `mcpq_audit_contracts` | 输出确定性与语义问题、证据和可复现分数。 | 审查含糊、重叠、误导说明和注解语义。 |
| `mcpq_compare_contracts` | 比较两个已注册版本并识别兼容性变化。 | 解释语义变化并建议迁移步骤。 |
| `mcpq_generate_probe_suite` | 生成普通、边界、错误和对抗用例，但不执行。 | 生成场景化用例和预期结果；本地代码负责最终验收。 |

完整的输入、输出、不变量和错误行为见
[`docs/design.md`](docs/design.md)。

## 当前能力

| 能力 | 状态 |
| --- | --- |
| TypeScript 包和本地 stdio transport | 已完成 |
| 4 个带输入/输出 Schema 的可发现工具 | 已完成 |
| 带路径、环境和资源上限的严格目标注册表 | 已完成 |
| MCP initialize 与 `tools/list` 检查 | 已完成 |
| 超时、异常 JSON、stdout 污染、输出上限和进程清理 | 已完成 |
| 确定性规则与可复现评分卡 | 已完成 |
| 严格验证、可安全降级的 Hy3 语义审计 | 已完成 |
| 确定性兼容性比较和可选 Hy3 迁移审查 | 已完成 |
| 经本地 Schema 与安全策略验证的惰性探针 | 已完成 |
| 10 个 fixture 的可复现评测与基线 | 已完成 |
| Cursor 和 CodeBuddy 项目级配置 | 已完成 |
| Cursor 与 CodeBuddy 真实只读 fixture 调用 | 已验证 |
| 干净 tarball 安装、脱敏证据与最终 GIF | 已验证 |

`mcpq_audit_contracts` 设置 `include_hy3=false` 时可完全离线运行。设置为
`true` 后，如果 Hy3 未配置、不可达、超时或返回无效内容，确定性结果仍会保留，
状态会安全降级为 `partial`，系统不会伪造语义问题。

`mcpq_compare_contracts` 同样支持 `include_hy3=false`。删除工具、增加必填
输入、收窄约束、移除 enum 值、收窄输出和提高风险注解等变化由本地代码分类。
Hy3 可以补充语义风险和迁移步骤，但不能修改确定性 breaking 结论。

`mcpq_generate_probe_suite` 的核心是 Hy3 生成，因此需要 Hy3。每个候选用例都
必须通过本地输入 Schema、场景类型、数量、证据指针和安全策略验证。结果只是
惰性数据，质量门禁不会调用目标工具。

## 开发、演示与交付检查

要求 Node.js 22 或更新版本以及 npm。

```bash
cd mcp_servers/mcp_quality_gate
npm ci
npm run typecheck
npm run lint
npm test
npm run evaluate
```

一条命令运行完整离线演示：发现 4 个工具、检查合规 fixture、审计故障
fixture，并比较一个 breaking 版本：

```bash
npm run demo
```

一条命令验证阶段 8 交付：构建、检查双客户端配置、进行真实 stdio 握手、发现
4 个工具，并调用 `fixture-good`：

```bash
npm run verify:delivery
```

## Cursor 与 CodeBuddy

仓库根目录包含两个可提交、无密钥、仅使用相对路径的项目配置：

- Cursor：`/.cursor/mcp.json`
- CodeBuddy：`/.mcp.json`

先在子项目中运行 `npm ci && npm run build`，再从**仓库根目录**启动客户端。
首次连接时，客户端会要求批准项目 MCP Server。Node.js 必须存在于客户端的
`PATH` 中。

验证工具发现：

```bash
agent mcp enable hy3-mcp-quality-gate
agent mcp list
agent mcp list-tools hy3-mcp-quality-gate

codebuddy mcp list
codebuddy mcp get hy3-mcp-quality-gate
```

可直接向 Agent 提出：

```text
调用 mcpq_inspect_server，target_id 使用 fixture-good，
include_schemas 使用 false，只汇报 status 和发现的工具名。
```

完整安装、批准、调用和故障排查步骤见
[`docs/clients.md`](docs/clients.md)。

### 脱敏客户端演示

![Cursor、CodeBuddy 与干净安装验证](assets/client-demo.gif)

GIF 由规范化终端证据可复现地渲染，只包含合成 fixture ID，不包含账号、凭据、
个人路径或原始模型对话。验收项与证据规则见
[`docs/delivery.md`](docs/delivery.md)。

## 配置真实检查目标

从 [`examples/targets.example.json`](examples/targets.example.json) 复制一份
私有注册表，例如 `targets.json`。真实注册表已经被 `.gitignore` 忽略，不要
提交它。命令、工作目录、固定环境变量和资源限制只能通过启动注册表提供；MCP
调用者只能选择经过验证的 `target_id`。

```bash
MCPQ_TARGETS_FILE=/absolute/path/to/targets.json npm start
```

要启用 Hy3 语义路径，向启动客户端的进程环境提供：

```bash
export HY3_API_KEY=EMPTY
export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_MODEL=hy3
export HY3_REASONING_EFFORT=high
export HY3_TIMEOUT_MS=60000
```

只有不验证身份的本地端点才适合使用 `EMPTY`。需要鉴权时必须使用真实凭据，
并只放在进程环境中，绝不能写入注册表、客户端配置、日志、评测或验证记录。

## 核心设计原则

1. **事实与判断分离。** 每条问题明确标记来源是确定性代码还是 Hy3。
2. **证据必填。** 问题必须关联协议事件、JSON Pointer、工具名或版本变化。
3. **命令属于配置。** 调用者只能提交可信 `target_id`，不能传入 shell 命令。
4. **默认非侵入。** 只做初始化和发现，不调用目标业务工具。
5. **不可信文本只能作为数据。** 目标说明、Schema、stderr 和模型输出不能
   改写门禁指令。
6. **评分可复现。** 只有确定性问题改变数字分数，Hy3 问题单独报告置信度。

## 架构

```text
MCP 客户端
    |
    | stdio tools/call
    v
Hy3 MCP 质量门禁
    |-- 可信本地目标注册表
    |-- 有界 stdio 检查器
    |-- 确定性规则引擎
    |-- 确定性兼容性引擎
    |-- Hy3 语义与迁移审查器
    |-- 经本地验证的惰性探针生成器
    `-- 结构化报告组合器
             |
             v
       问题 + 分数 + 证据
```

## 安全边界

质量门禁会启动配置好的本地进程，因此安全边界属于产品本身：

- 只解析本地注册表中已知的目标 ID；
- 不经 shell 启动子进程；
- 只继承明确允许的环境变量；
- 限制启动、请求、总运行时间以及 stdout/stderr 大小；
- 超时时终止完整子进程组；
- 在日志、报告和 Hy3 请求之前清理凭据与个人路径；
- stdout 只允许 MCP JSON-RPC，诊断信息写入 stderr；
- MCP annotations 只是不可信提示；
- 不调用目标业务工具。

威胁、控制和剩余风险见 [`docs/security.md`](docs/security.md)。

## 阶段路线

- 阶段 1：设计、工具合约、威胁模型、规则目录和注册表示例。
- 阶段 2：可运行 TypeScript stdio Server 和 4 个工具。
- 阶段 3：有界目标进程管理与协议检查。
- 阶段 4：确定性审计、证据模型和可复现分数。
- 阶段 5：严格验证、可安全降级的 Hy3 语义审计。
- 阶段 6：兼容性比较与安全惰性探针。
- 阶段 7：故障 fixture、严格 golden 预期和可复现评测。
- 阶段 8（已完成）：干净包验证、Cursor/CodeBuddy 真实只读 fixture 调用、
  双语文档、脱敏证据与可复现 GIF。

## 非目标

- Web 仪表盘或托管服务；
- 自动修改目标源码；
- 从 MCP 参数接受任意命令；
- 自动执行生成探针或破坏性目标工具；
- 声称 MCP annotations 能证明真实运行行为；
- 替代官方 MCP SDK 或 Inspector；
- 评价与公开 MCP 合约无关的一般代码质量。

## 环境变量

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `HY3_API_KEY` | 未设置 | 非空时启用语义审查。 |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-compatible API 根地址；拒绝凭据、query 和 fragment。 |
| `HY3_MODEL` | `hy3` | 发送给端点的模型 ID。 |
| `HY3_REASONING_EFFORT` | `high` | `no_think`、`low` 或 `high`。 |
| `HY3_TIMEOUT_MS` | `60000` | 整个请求响应期限，最大 300000 ms。 |
| `MCPQ_TARGETS_FILE` | 未设置 | 本地目标注册表路径。 |

## 文档

- [架构与工具合约](docs/design.md)
- [安全模型](docs/security.md)
- [规则目录](docs/rule-catalog.md)
- [评测方法与基线解释](docs/evaluation.md)
- [Cursor 与 CodeBuddy 配置及可运行调用](docs/clients.md)
- [交付验证与证据策略](docs/delivery.md)
- [目标注册表示例](examples/targets.example.json)
