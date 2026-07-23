\# 示例 4：工具调用



\## 功能说明

演示如何让 Hy3 调用外部工具（函数）来获取实时信息或执行计算。模型会自主判断是否需要调用工具，并生成符合工具格式的调用请求。



\## 适用场景

\- 获取实时信息（天气、时间、股票等）

\- 执行数学计算

\- 数据库查询

\- 调用第三方 API

\- 任何需要外部数据或计算的任务



\## 完整请求



\### 1. 定义工具



```python

tools = \[

&#x20;   {

&#x20;       "type": "function",

&#x20;       "function": {

&#x20;           "name": "get\_current\_time",

&#x20;           "description": "获取当前日期和时间",

&#x20;           "parameters": {

&#x20;               "type": "object",

&#x20;               "properties": {

&#x20;                   "format": {

&#x20;                       "type": "string",

&#x20;                       "enum": \["full", "date", "time"],

&#x20;                       "description": "时间格式"

&#x20;                   }

&#x20;               }

&#x20;           }

&#x20;       }

&#x20;   },

&#x20;   {

&#x20;       "type": "function",

&#x20;       "function": {

&#x20;           "name": "calculate",

&#x20;           "description": "执行数学运算",

&#x20;           "parameters": {

&#x20;               "type": "object",

&#x20;               "properties": {

&#x20;                   "operation": {

&#x20;                       "type": "string",

&#x20;                       "enum": \["add", "subtract", "multiply", "divide"],

&#x20;                       "description": "运算类型"

&#x20;                   },

&#x20;                   "a": {"type": "number"},

&#x20;                   "b": {"type": "number"}

&#x20;               },

&#x20;               "required": \["operation", "a", "b"]

&#x20;           }

&#x20;       }

&#x20;   }

]

```



\### 2. 发起带工具的请求



```python

response = client.chat.completions.create(

&#x20;   model=MODEL,

&#x20;   messages=\[{"role": "user", "content": "现在几点了？"}],

&#x20;   tools=tools,

&#x20;   tool\_choice="auto",  # 让模型自主决定是否调用工具

&#x20;   temperature=0.7,

&#x20;   max\_tokens=200,

&#x20;   extra\_body={"chat\_template\_kwargs": {"reasoning\_effort": "no\_think"}}

)

```



\### 3. 处理工具调用（多轮循环）



```python

if response.choices\[0].message.tool\_calls:

&#x20;   # 获取工具调用信息

&#x20;   tool\_call = response.choices\[0].message.tool\_calls\[0]

&#x20;   func\_name = tool\_call.function.name

&#x20;   args = json.loads(tool\_call.function.arguments)

&#x20;   

&#x20;   # 执行对应的工具

&#x20;   if func\_name == "get\_current\_time":

&#x20;       result = get\_current\_time(args.get("format", "full"))

&#x20;   elif func\_name == "calculate":

&#x20;       result = calculate(args\["operation"], args\["a"], args\["b"])

&#x20;   

&#x20;   # 将工具结果返回给模型

&#x20;   messages.append(response.choices\[0].message)

&#x20;   messages.append({

&#x20;       "role": "tool",

&#x20;       "tool\_call\_id": tool\_call.id,

&#x20;       "content": result

&#x20;   })

&#x20;   

&#x20;   # 让模型基于工具结果生成最终回复

&#x20;   final = client.chat.completions.create(

&#x20;       model=MODEL,

&#x20;       messages=messages,

&#x20;       temperature=0.7,

&#x20;       max\_tokens=200,

&#x20;       extra\_body={"chat\_template\_kwargs": {"reasoning\_effort": "no\_think"}}

&#x20;   )

```



\## 响应解析



\### 模型响应中的 tool\_calls



| 字段 | 说明 |

|------|------|

| `tool\_calls\[0].function.name` | 要调用的工具名称 |

| `tool\_calls\[0].function.arguments` | 调用参数（JSON 字符串） |

| `tool\_calls\[0].id` | 工具调用唯一标识（用于匹配结果） |



\### 工具结果回传



| 字段 | 说明 |

|------|------|

| `role: "tool"` | 标识为工具返回结果 |

| `tool\_call\_id` | 对应工具调用的 ID |

| `content` | 工具执行结果（字符串） |



\## 工具调用流程图



```

用户提问 → 模型判断是否需要工具

&#x20;               ↓

&#x20;          需要调用工具

&#x20;               ↓

&#x20;   模型返回 tool\_calls（工具名称 + 参数）

&#x20;               ↓

&#x20;   开发者执行对应的工具函数

&#x20;               ↓

&#x20;   将工具结果以 "tool" 角色回传给模型

&#x20;               ↓

&#x20;   模型基于工具结果生成最终回复

&#x20;               ↓

&#x20;           返回用户

```



\## 示例输出



```text

&#x20;示例 1: 查询当前时间

\---

用户: 现在几点了？

调用工具: get\_current\_time({'format': 'time'})

工具返回: 20:39:59

AI 回复: 现在是 \*\*20:39\*\*（晚上 8 点 39 分）。



&#x20;示例 2: 数学计算

\---

用户: 25 乘以 37 等于多少？

调用工具: calculate({'operation': 'multiply', 'a': 25, 'b': 37})

计算结果: 925

AI 回复: 25 × 37 = \*\*925\*\*。

```



\## 关键要点



1\. \*\*工具定义\*\*：使用 OpenAI 兼容的 function 格式

2\. \*\*自动决策\*\*：设置 `tool\_choice="auto"` 让模型自主判断

3\. \*\*多轮循环\*\*：模型可能连续调用多个工具

4\. \*\*结果回传\*\*：必须以 `"role": "tool"` 格式返回

5\. \*\*必填参数\*\*：在 `required` 数组中声明

