\# 示例 3：流式 vs 非流式对比



\## 功能说明

通过同一个问题，分别使用流式和非流式两种方式请求，对比首 Token 时延、总耗时、输出长度等关键指标，帮助开发者根据场景选择合适的方式。



\## 适用场景

\- 接口选型评估

\- 性能测试

\- 用户体验优化决策



\## 完整请求



\### 非流式请求



```python

response = client.chat.completions.create(

&#x20;   model=MODEL,

&#x20;   messages=\[{"role": "user", "content": prompt}],

&#x20;   temperature=0.7,

&#x20;   max\_tokens=150,

&#x20;   extra\_body={"chat\_template\_kwargs": {"reasoning\_effort": "no\_think"}}

)

\# 等待完整响应后一次性返回

```



\### 流式请求



```python

stream = client.chat.completions.create(

&#x20;   model=MODEL,

&#x20;   messages=\[{"role": "user", "content": prompt}],

&#x20;   temperature=0.7,

&#x20;   max\_tokens=150,

&#x20;   stream=True,

&#x20;   extra\_body={"chat\_template\_kwargs": {"reasoning\_effort": "no\_think"}}

)



first\_token\_time = None

for chunk in stream:

&#x20;   if first\_token\_time is None and chunk.choices\[0].delta.content:

&#x20;       first\_token\_time = time.time()

&#x20;   if chunk.choices\[0].delta.content:

&#x20;       content += chunk.choices\[0].delta.content

```



\## 响应解析



\### 非流式响应

| 字段 | 说明 |

|------|------|

| `response.choices\[0].message.content` | 完整回复内容 |

| `response.usage.total\_tokens` | 总 Token 消耗量 |

| `elapsed\_time` | 从请求到收到完整响应的总耗时 |



\### 流式响应

| 字段 | 说明 |

|------|------|

| `first\_token\_time` | 收到第一个内容块的时间 |

| `first\_token\_latency` | 首 Token 时延（= first\_token\_time - start\_time）|

| `elapsed\_time` | 收到完整响应的总耗时 |

| `chunk\_count` | 响应被拆分的块数 |



\## 示例输出



```text

&#x20;测试 Prompt: 什么是微服务架构？请用 100 字左右概括其主要特点。



&#x20;非流式模式:

&#x20;   完成 (3.12秒)

&#x20;  内容: 微服务架构是将单一应用拆分为多个小型、独立服务的设计模式...

&#x20;   Token: 91



&#x20;流式模式:

&#x20;   完成 (3.76秒)

&#x20;   首 Token 时延: 2.40秒

&#x20;   内容: 微服务架构是将单一应用拆分为多个小型、独立服务的设计模式...

&#x20;  长度: 101 字符



&#x20;对比结果:

&#x20;  非流式总耗时: 3.12秒

&#x20;  流式总耗时: 3.76秒

&#x20;  流式首 Token 时延: 2.40秒

```



\## 结论与建议



| 场景 | 推荐方式 | 原因 |

|------|----------|------|

| 实时对话/聊天 | 流式  | 用户能立即看到回复，体验好 |

| 后台批量处理 | 非流式 | 代码简单，总耗时略短 |

| 长文本生成 | 流式 | 用户可提前阅读，等待感弱 |

| API 网关/代理 | 非流式 | 处理逻辑简单，无需流式协议 |



> \*\*核心原则\*\*：流式优化的是"首屏体验"，非流式优化的是"总完成时间"。

