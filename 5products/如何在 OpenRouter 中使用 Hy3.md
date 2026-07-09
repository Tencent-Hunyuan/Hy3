- # 如何在 OpenRouter 中使用 Hy3

  本文档旨在指导用户如何在 OpenRouter 中配置并运行 Hy3 (295B-A21B) 模型，涵盖从环境搭建到实际业务场景落地的完整流程。

  ## 1. 安装与版本要求
  在开始之前，请确保你的环境满足以下要求：
  - **软件版本**：无。
  - **网络环境**：需能够访问 OpenRouter 。
  - **账号准备**：已注册 OpenRouter账号，并获取了有效的 API Key。

  ## 2. 核心配置项
  请按照以下步骤在 OpenRouter 中配置 Hy3 模型参数：

  | 配置项              | 填写内容 / 说明                                              |
  | :------------------ | :----------------------------------------------------------- |
  | **API Base URL**    | `https://openrouter.ai/api/v1` (或你的本地 vLLM/SGLang 地址) |
  | **Model Name**      | hy3                                                          |
  | **API Key / Token** | 输入你在 OpenRouter 获取的密钥                               |
  | **协议选择**        | OpenAI Compatible / Chat Completion                          |

  > **⚠️ 常见注意事项：**
  > 1. **上下文长度**：Hy3 支持长上下文，建议在设置中将 `Max Tokens` 或 `Context Window` 设置为 8192 或更高以发挥优势。
  > 2. **温度设置**：如果是代码生成任务，建议 Temperature 设为 0.2-0.4；如果是创意写作，建议设为 0.7-0.9。
  > 3. **流式输出**：务必开启 Stream 模式，否则大模型响应时间过长会导致超时。

  ![1783565666822](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783565666822.png)
  *(图注：在 OpenRouter中添加自定义模型的配置界面,这里需要你在进入主页的时候点explore model,然后点开add model选择hy3,将鼠标光标移动到三个点的位置点开advanced setting,按照图片那样配置)*

  ## 3. 第一次对话测试
  配置完成后，进行连通性测试。请在对话框中输入以下 Prompt：

  > **Prompt:** "你好，请简单介绍一下你自己，并输出数字1"

  **预期结果**：模型应准确回答它是 Hy3，且输出数字1。

  ![1783566590643](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783566590643.png)

  ## 4. 端到端实战任务 Demo
  为了验证 Hy3 在实际场景中的能力，我们执行了一个 分析任务。

  **任务背景**：使用表格列出Transformer和MoE的区别和彼此的优势

  **操作步骤**：
  1. 把鼠标光标移动到上面的三点，选择duplicate复制新会话（假设你是完成第一次对话任务后执行该任务，或者重新开对话调好参数也可以）

  2. 输入以下内容：请全面对比稠密Transformer模型与MoE混合专家模型，从架构原理、参数激活方式、算力开销、显存占用、扩展能力、推理速度、适用场景7个维度整理，以标准Markdown表格输出，内容专业准确。

  3. 然后再次输入内容：**"根据上述对比结论，假设我是一家跨境电商公司的AI架构师，当前面临以下需求：**

     1. 需部署一个**支持256K上下文**的商品评论情感分析模型（日均请求量 50万次）
     2. 服务器预算限制：**单次推理成本 ≤ 0.0002元**（参考阿里云百炼平台定价）
     3. 必须保证**95%+的负面评论召回率**（避免漏检差评）

     **请完成以下端到端任务：**
     a) 从**稠密模型 vs MoE** 中选择架构，并用**3条数据证明你的选择**（需引用对比表格中的维度）
     b) 输出**可直接部署的vLLM配置代码**（含模型加载、路由策略、批处理参数）
     c) 给出**压测验证方案**（用Python代码模拟50万请求，验证成本与召回率）"

  **最终效果展示**：
  *(此处插入 GIF 动图或多张连续截图，展示从输入到输出的全过程)*

  ![1783566881647](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783566881647.png)

  ![1783567459465](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783567459465.png)


![1783568103427](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783568103427.png)

![1783568130382](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783568130382.png)

![1783568167847](C:\Users\Mechanist\AppData\Roaming\Typora\typora-user-images\1783568167847.png)

