Hy3 API 快速上手文档

&#x20;

1\. 基础配置信息

&#x20;

接口基础地址

&#x20;

plaintext

&#x20; 

BASE\_URL = "https://hy3.example.com/v1"

 

&#x20;

鉴权方式

&#x20;

使用 API Key 放在请求头中：

&#x20;

plaintext

&#x20; 

Authorization: Bearer ${API\_KEY}

 

&#x20;

可用模型

&#x20;

\- hy3-base：通用对话基础模型

\- hy3-reason：增强思考推理模型

&#x20;

限流说明

&#x20;

默认限制：60 请求/分钟，超出限制将返回 429 错误。

&#x20;

2\. 最小可运行示例

&#x20;

2.1 curl 命令示例

&#x20;

bash

&#x20; 

curl https://hy3.example.com/v1/chat/completions \\

&#x20; -H "Authorization: Bearer 你的API\_KEY" \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{

&#x20;   "model": "hy3-base",

&#x20;   "messages": \[{"role": "user", "content": "你好"}],

&#x20;   "temperature": 0.7,

&#x20;   "max\_tokens": 512

&#x20; }'

 

&#x20;

2.2 Python OpenAI SDK 示例

&#x20;

python

&#x20; 

from openai import OpenAI

import os



client = OpenAI(

&#x20;   base\_url="https://hy3.example.com/v1",

&#x20;   api\_key=os.getenv("HY3\_API\_KEY")

)



resp = client.chat.completions.create(

&#x20;   model="hy3-base",

&#x20;   messages=\[{"role": "user", "content": "你好"}],

&#x20;   temperature=0.7,

&#x20;   max\_tokens=512,

&#x20;   stream=False

)

print(resp.choices\[0].message.content)

 

&#x20;

3\. 关键参数说明

&#x20;

\-  temperature ：控制回答随机性，取值 0\~1，数值越低回答越确定

\-  top\_p ：核采样参数，控制备选词汇的范围

\-  max\_tokens ：单次请求最大输出 token 长度

\-  stream ：设为 true 开启流式逐块返回

\-  tools ：用于函数工具调用能力

\-  reasoning\_mode ：开启/关闭深度思考推理模式

&#x20;

4\. 常见报错排查

&#x20;

1. 401：API Key 错误或为空，请检查鉴权配置

2. 429：触发接口限流，需添加重试退避逻辑

3. 400：请求体参数不合法，请检查字段格式

4. 网络超时：增加 timeout 配置，配合重试机制

&#x20;

5\. 配套示例目录

&#x20;

所有完整案例代码存放于  /examples  文件夹：

&#x20;

1. basic\_chat：单轮、多轮基础对话

2. streaming\_chat：流式逐 chunk 输出

3. stream\_vs\_normal：流式与非流式时延对比

4. tool\_calling：工具调用多轮循环

5. reasoning\_switch：思考模式开关对比

6. error\_retry：异常捕获与自动重试

