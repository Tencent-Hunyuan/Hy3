# 如何在 CodeBuddyIDE中使用 Hy3

本文档旨在指导用户如何在 CodeBuddyIDE 中配置并运行 Hy3 (295B-A21B) 模型，涵盖从环境搭建到实际业务场景落地的完整流程。

## 1. 安装与版本要求
在开始之前，请确保你的环境满足以下要求：
- **软件版本**：CodeBuddyIDEv4.9.15及以上版本（推荐最新版）。
- **网络环境**：需能够访问 [OpenRouter / 本地部署地址 / SiliconFlow]。
- **账号准备**：已注册微信账号，并获取了有效的 API Key（如适用）。

## 2. 核心配置项
请按照以下步骤在 CodeBuddyIDE中配置 Hy3 模型参数(其实没什么好配的，建议直接跳过)：

| 配置项              | 填写内容 / 说明                                              |
| :------------------ | :----------------------------------------------------------- |
| **API Base URL**    | `https://openrouter.ai/api/v1` (或你的本地 vLLM/SGLang 地址) |
| **Model Name**      | `tencent/hy3-295b-a21b` (注意大小写，需与服务商一致)         |
| **API Key / Token** | 输入你在 [服务商名称] 获取的密钥                             |
| **协议选择**        | OpenAI Compatible / Chat Completion                          |

> **⚠️ 常见注意事项：**
> 1. **上下文长度**：Hy3 支持长上下文，建议在设置中将 `Max Tokens` 或 `Context Window` 设置为 8192 或更高以发挥优势。
> 2. **温度设置**：如果是代码生成任务，建议 Temperature 设为 0.2-0.4；如果是创意写作，建议设为 0.7-0.9。
> 3. **流式输出**：务必开启 Stream 模式，否则大模型响应时间过长会导致超时。

## 3. 第一次对话测试
配置完成后，进行连通性测试。请在对话框中输入以下 Prompt：

> **Prompt:** "你好，请简单介绍一下你自己，并输出数字1"

**预期结果**：模型应准确回答它是 Hy3，且输出数字1。

提问的时候把模式调成ask模式

![1783569179342](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783569179342.png)

## 4. 端到端实战任务 Demo
为了验证 Hy3 在实际场景中的能力，我们执行了一个 分析任务。

**任务背景**：transformer和MoE模型的对比

**操作步骤**：
1. 把模型调整为ask模式，然后输入请全面对比稠密Transformer模型与MoE混合专家模型，从架构原理、参数激活方式、算力开销、显存占用、扩展能力、推理速度、适用场景7个维度整理，以标准Markdown表格输出，内容专业准确。
2. 把模式调成craft模式，然后输入

**最终效果展示**：
*(此处插入 GIF 动图或多张连续截图，展示从输入到输出的全过程)*

![1783570030998](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783570030998.png)

![1783570077775](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783570077775.png)

![1783570440088](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783570440088.png)

![1783570471398](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783570471398.png)

![1783570497700](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783570497700.png)

![1783570538477](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783570538477.png)

![1783570558799](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783570558799.png)

## 5. 总结
通过上述配置，你可以在CodeBuddyIDE中充分利用 Hy3 的 [推理/Agent/长文本] 能力，有效提升 [工作效率/开发体验]。