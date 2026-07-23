\# 示例 1：基础聊天



\## 功能说明

演示 Hy3 的单轮对话和多轮对话能力。



\## 完整请求

单轮对话使用 `messages` 传入单条用户消息；多轮对话通过追加 `assistant` 和 `user` 消息实现上下文传递。



\## 响应解析

\- `content`: 模型生成的回复

\- `finish\_reason`: stop（正常结束）/ length（达到长度限制）

\- `usage`: Token 用量统计



\## 示例输出

标题: 单轮对话

回复: RESTful API 是一种基于 HTTP 协议，以资源为中心并通过标准方法（如 GET、POST、PUT、DELETE）进行无状态交互的 Web 接口设计风格。

结束原因: stop

Token 用量: total\_tokens=60



标题: 多轮 - 第1轮

回复: 在 Python 中读取 CSV 文件有多种方式...

结束原因: length

Token 用量: total\_tokens=331

