# Dify × Hy3

[Dify](https://dify.ai) 是低代码 LLM 应用平台。把 Hy3 加为「自定义 OpenAI 兼容模型」后，可搭聊天机器人或 Agent（适合作为小作品宿主）。

## 安装与版本

| 项 | 要求 |
|----|------|
| 部署 | [Dify Cloud](https://cloud.dify.ai) 或 Docker 自托管 |
| 版本 | 支持 OpenAI-API-compatible 供应商的近期版本 |
| Key | TokenHub 或 OpenRouter |

自托管可参考官方 Docker Compose；云版直接登录即可。

## 配置项

路径通常为：`设置` → `模型供应商` → `添加` → **OpenAI-API-compatible**（名称因版本略有差异）。

### TokenHub

| 配置 | 值 |
|------|-----|
| API Endpoint / Base URL | `https://tokenhub.tencentmaas.com/v1` |
| API Key | TokenHub Key |
| Model Name | `hy3` |
| 协议 | OpenAI 兼容 |

### OpenRouter

| 配置 | 值 |
|------|-----|
| API Endpoint | `https://openrouter.ai/api/v1` |
| API Key | `sk-or-...` |
| Model Name | `tencent/hy3` |
| 协议 | OpenAI 兼容 |

保存后在「模型」列表中应能看到 Hy3，并用于应用编排。

## 第一次对话

1. 创建「聊天助手」应用，模型选 Hy3。  
2. 系统提示：`你是简洁的中文助手。`  
3. 用户消息：`用三句话介绍你自己。`  
4. 在预览对话中确认回复。

**截图：** `assets/dify-first-chat.png`

## 端到端任务 Demo

**任务：** 做一个「会议纪要提炼」工作流。

1. 新建 Workflow / Chatflow。  
2. 节点：开始 → LLM（Hy3）→ 结束。  
3. LLM 提示词：

```text
将用户粘贴的会议记录整理为：
1) 决议事项（条目）
2) 待办（负责人 + 动作）
3) 风险
若信息不足，明确写出「缺失：…」。
```

4. 粘贴一段示例会议记录，跑通一次。  
5. （可选）加「知识库」或 HTTP 工具节点，体现 Agent 能力。

**截图：** `assets/dify-meeting-demo.png`

## 注意事项

- Base URL 填到 `/v1` 为止，不要重复 `/v1/chat/completions`（视 Dify 表单说明而定）。
- 模型名：TokenHub=`hy3`，OpenRouter=`tencent/hy3`。
- 超时：长文/思考模式需调大 LLM 节点超时与 max tokens。
- 自托管需确保容器能访问外网 TokenHub/OpenRouter。
- 生产环境用密钥管理，勿把 Key 写进应用导出 JSON 后公开上传。

## 截图清单

| 文件 | 内容 |
|------|------|
| `assets/dify-provider.png` | 模型供应商配置（Key 打码） |
| `assets/dify-first-chat.png` | 第一次对话 |
| `assets/dify-meeting-demo.png` | 会议纪要工作流结果 |

## 与小作品的关系

独立仓库 **Hy3 Workbench** 演示了同一套 TokenHub 能力（思考 + 工具调用）。若你更熟 Dify，也可把同等提示词迁到 Dify Agent，作为 Part B 的另一种形态；本仓库 Part B 默认以独立 Web 应用交付。
