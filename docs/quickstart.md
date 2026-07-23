\# Hy3 API Quickstart



> 5 分钟跑通第一次调用，半小时上手主要能力





\## 目录



\- \[基础信息](#基础信息)

\- \[快速开始](#快速开始)

\- \[参数说明](#参数说明)

\- \[示例集合](#示例集合)

\- \[常见报错排查](#常见报错排查)





\## 基础信息



\### 接入配置



| 配置项 | 值 | 说明 |

|--------|-----|------|

| Base URL | `https://tokenhub.tencentmaas.com/v1` | API 端点地址 |

| API Key | 从控制台获取 | 身份认证密钥 |

| Model | `hy3` | 模型名称 |

| 超时时间 | 建议 60 秒 | 避免请求被中断 |



\### 速率限制



| 限制项 | 限制值 | 说明 |

|--------|--------|------|

| 请求频率 | 视套餐而定 | 超出会返回 429 |

| 最大输入 Token | 视套餐而定 | 超出会截断 |

| 最大输出 Token | 视套餐而定 | 可通过 max\_tokens 控制 |





\## 快速开始



\### 方式一：curl（命令行）



```bash

curl https://tokenhub.tencentmaas.com/v1/chat/completions \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -H "Authorization: Bearer 你的API密钥" \\

&#x20; -d '{

&#x20;   "model": "hy3",

&#x20;   "messages": \[

&#x20;     {"role": "user", "content": "用一句话介绍人工智能"}

&#x20;   ],

&#x20;   "temperature": 0.7,

&#x20;   "max\_tokens": 100,

&#x20;   "extra\_body": {

&#x20;     "chat\_template\_kwargs": {

&#x20;       "reasoning\_effort": "no\_think"

&#x20;     }

&#x20;   }

&#x20; }'

```



\### 方式二：Python（OpenAI SDK）



\#### 1. 安装依赖



```bash

pip install openai python-dotenv

```



\#### 2. 配置环境变量



创建 `.env` 文件：



```env

HY3\_BASE\_URL=https://tokenhub.tencentmaas.com/v1

HY3\_API\_KEY=你的API密钥

HY3\_MODEL=hy3

```



\#### 3. 最小可运行示例



```python

import os

from openai import OpenAI

from dotenv import load\_dotenv



load\_dotenv()



client = OpenAI(

&#x20;   base\_url=os.getenv("HY3\_BASE\_URL"),

&#x20;   api\_key=os.getenv("HY3\_API\_KEY"),

&#x20;   timeout=60.0

)



response = client.chat.completions.create(

&#x20;   model=os.getenv("HY3\_MODEL", "hy3"),

&#x20;   messages=\[

&#x20;       {"role": "user", "content": "用一句话介绍人工智能"}

&#x20;   ],

&#x20;   temperature=0.7,

&#x20;   max\_tokens=100,

&#x20;   extra\_body={"chat\_template\_kwargs": {"reasoning\_effort": "no\_think"}}

)



print(response.choices\[0].message.content)

```



\#### 4. 运行



```bash

python your\_script.py

```





\## 参数说明



\### 核心参数



| 参数 | 类型 | 必填 | 说明 | 示例 |

|------|------|------|------|------|

| model | string | 是 | 模型名称 | `"hy3"` |

| messages | array | 是 | 对话消息列表 | `\[{"role":"user","content":"你好"}]` |

| temperature | float | 否 | 随机性，0-1，越高越随机 | `0.7` |

| top\_p | float | 否 | 核采样概率，0-1 | `0.9` |

| max\_tokens | int | 否 | 最大输出 Token 数 | `200` |

| stop | string/array | 否 | 停止词，遇到即停止 | `\["\\n", "END"]` |

| stream | bool | 否 | 是否流式输出 | `True` / `False` |

| tools | array | 否 | 工具定义列表 | 见工具调用示例 |

| reasoning\_effort | string | 否 | 思考模式：no\_think / low / high | `"no\_think"` |



\### Messages 格式



```python

messages = \[

&#x20;   {"role": "system", "content": "你是一个编程助手"},

&#x20;   {"role": "user", "content": "你好"},

&#x20;   {"role": "assistant", "content": "你好！有什么可以帮助你的？"},

&#x20;   {"role": "user", "content": "Python 怎么读取 CSV？"}

]

```



| Role | 说明 |

|------|------|

| system | 系统提示，设定 AI 的角色和行为 |

| user | 用户消息 |

| assistant | 模型的回复（用于多轮对话） |

| tool | 工具调用结果（用于工具调用场景） |





\## 示例集合



| 示例 | 文件 | 说明 |

|------|------|------|

| 基础聊天 | `quickstart/01\_basic\_chat.py` | 单轮 + 多轮对话 |

| 流式请求 | `quickstart/02\_streaming.py` | 逐字输出，提升体验 |

| 流式 vs 非流式 | `quickstart/03\_compare.py` | 对比首 Token 时延和总耗时 |

| 工具调用 | `quickstart/04\_tool\_calling.py` | 调用外部函数 |

| 推理模式 | `quickstart/05\_reasoning.py` | no\_think / low / high 对比 |

| 错误处理 | `quickstart/06\_error\_handling.py` | 重试与退避策略 |



每个示例都配有详细的 `.md` 说明文档，位于 `docs/` 目录下。





\## 常见报错排查



\### 1. 认证错误



\*\*错误信息：\*\*

```

AuthenticationError: Invalid API key

```



\*\*原因：\*\* API Key 不正确或已过期



\*\*解决方法：\*\*

\- 检查 `.env` 文件中的 `HY3\_API\_KEY` 是否正确

\- 确认 API Key 是否已激活

\- 尝试重新生成 API Key





\### 2. 限流错误



\*\*错误信息：\*\*

```

RateLimitError: Rate limit exceeded

```



\*\*原因：\*\* 请求频率超过限制



\*\*解决方法：\*\*

\- 降低请求频率

\- 实现指数退避重试（见示例 6）

\- 升级套餐获取更高配额





\### 3. 超时错误



\*\*错误信息：\*\*

```

APITimeoutError: Request timed out

```



\*\*原因：\*\* 网络延迟或服务响应慢



\*\*解决方法：\*\*

\- 增加 `timeout` 参数（如 60 秒）

\- 检查网络连接

\- 使用流式模式获取更快反馈





\### 4. 模型名称错误



\*\*错误信息：\*\*

```

NotFoundError: Model 'xxx' not found

```



\*\*原因：\*\* 模型名称拼写错误



\*\*解决方法：\*\*

\- 确认模型名称为 `hy3`

\- 检查是否有额外空格





\### 5. Token 超限



\*\*错误信息：\*\*

```

BadRequestError: Input tokens exceed limit

```



\*\*原因：\*\* 输入或输出 Token 超出模型限制



\*\*解决方法：\*\*

\- 减少输入内容长度

\- 减小 `max\_tokens` 值

\- 截断过长的对话历史





\### 6. 连接错误



\*\*错误信息：\*\*

```

APIConnectionError: Connection refused

```



\*\*原因：\*\* 无法连接到 API 服务



\*\*解决方法：\*\*

\- 检查 Base URL 是否正确

\- 确认网络环境（是否需要代理）

\- 检查防火墙设置





\### 快速排查清单



\- \[ ] Base URL 是否正确？

\- \[ ] API Key 是否有效？

\- \[ ] 模型名称是否为 `hy3`？

\- \[ ] 网络是否正常？

\- \[ ] 是否在虚拟环境中？

\- \[ ] 依赖包是否已安装？





\## 更多资源



\- 完整示例代码：`quickstart/` 目录

\- 详细文档：`docs/` 目录

\- GitHub 仓库：\[Tencent-Hunyuan/Hy3](https://github.com/Tencent-Hunyuan/Hy3)

