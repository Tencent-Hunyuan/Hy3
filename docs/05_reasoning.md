\# 示例 5：推理模式对比



\## 功能说明

演示 Hy3 的三种推理模式（`no\_think`、`low`、`high`）的差异，包括 Token 消耗、是否输出思考过程、回答质量等方面的对比。



\## 适用场景

\- 需要模型展示推理步骤的教育/教学场景

\- 对 Token 成本敏感的应用

\- 需要调试模型思维链的场景



\## 完整请求



```python

response = client.chat.completions.create(

&#x20;   model=MODEL,

&#x20;   messages=\[{"role": "user", "content": prompt}],

&#x20;   temperature=0.7,

&#x20;   max\_tokens=400,

&#x20;   extra\_body={

&#x20;       "chat\_template\_kwargs": {

&#x20;           "reasoning\_effort": mode  # "no\_think" | "low" | "high"

&#x20;       }

&#x20;   }

)

```



\## 推理模式说明



| 模式 | 说明 | Token 消耗 | 思考过程 |

|------|------|-----------|---------|

| `no\_think` | 不输出推理过程，直接给出答案 | 最低  | 无 |

| `low` | 低强度推理，少量思考痕迹 | 中等 | 可能有 |

| `high` | 高强度推理，完整展示思考链 | 最高 | 有 |



\## 响应解析



| 字段 | 说明 |

|------|------|

| `message.content` | 模型的最终回答 |

| `message.reasoning\_content` 或 `message.reasoning` | 思考过程（如存在） |

| `usage.total\_tokens` | 总 Token 消耗量 |



\## 示例输出



```text

测试问题: 一个班级有 40 个学生，男生比女生多 6 人，问男生和女生各有多少人？



&#x20;推理模式: no\_think

&#x20;Token 用量: 238

&#x20;思考过程: 无（直接输出）

&#x20;回答预览: 设女生人数为 x，则男生为 x+6...



&#x20;推理模式: low

&#x20;Token 用量: 307

&#x20;思考过程: 无（直接输出）

&#x20;回答预览: 我们一步步来解这个题...



&#x20;推理模式: high

&#x20;Token 用量: 303

&#x20;思考过程: 有

&#x20;回答预览: 设女生人数为 x，则男生为 x+6...

```



\## 选择建议



| 场景 | 推荐模式 | 原因 |

|------|---------|------|

| 实时对话/聊天 | `no\_think` | 响应快，成本低 |

| 数学/逻辑问题 | `low` 或 `high` | 需要展示推导过程 |

| 教育/教学场景 | `high` | 展示完整思维链 |

| 成本敏感应用 | `no\_think` | Token 消耗最少 |

| 调试/分析 | `high` | 便于理解模型决策 |



\## 注意事项



1\. `reasoning\_content` 字段的具体名称可能因模型版本而异（`reasoning\_content` 或 `reasoning`）

2\. 并非所有模型版本都支持显示推理内容

3\. 推理内容不包含在 `content` 中，需要通过额外字段获取

