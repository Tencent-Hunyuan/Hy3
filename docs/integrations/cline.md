# Vscode Cline（Tencent Hy3）

> 本文档演示如何将腾讯混元 **Hy3**（295B MoE，256K 上下文，支持推理 / Agent / 工具调用 / 长文生成）接入 Cline，并跑通一个真实任务。

---

## 一、配置（Configuration）

Cline 可以使用 Openrouter，只需在模型设置里填入Openrouter 的api信息和model名称即可。

### 方式 Openrouter 

| 配置项 | 值 |
|--------|-----|
| **Base URL** | `https://openrouter.ai/api/v1/chat/completions` |
| **Model** | `tencent/hy3:free` |
| **API Key** | OpenRouter 申请的 Key（`sk-...` 格式） |
| **API Provider** | OpenRouter|


### 配置截图位置

![cline 模型设置](images/cline-config.png)


> 截图说明：在 Cline 设置，填入上表 OpenRouter / Model / API Key->done后设置成功。

---

## 二、首次对话（First Conversation）

配置完成后，新建一个对话，发送第一条消息验证模型已正确接入：

```
你：Hi

Hello! How can I help you today? Please let me know what you'd like to work on.
```
如果收到类似回复，说明 Hy3 已成功作为底层模型工作。

---

## 三、跑通真实任务（Real Task Demo）

**任务**：用 Cline + tencent/hy3:free 给项目 `Notes webapp pro` 添加实时预览能力。

### 3.1 任务指令（直接发给 WorkBuddy）

```
你是一个资深的前端工程师，请分析当前notes-webapp-pro项目
现在需要添加以下功能：
markdown的实时预览功能
请先给出修改方案，以及修改的文件
请不要重写整个项目，只修改必要部分
```

### 3.2 预期输出（Hy3 实际产出，节选）

> **Cline解析方案** 请确认解析方案：
> - **方案A**：引入marked CDN(联网，功能完整)，预览栏默认常驻双栏
> - **方案A**：引入markedCDN，并加预览开关按钮可隐藏
> - **方案B**：内联极简解析器(完全离线)，预览栏默认常驻双栏
> - **方案B**：内联极简解析器(离线)，并加预览开关按钮
>
> **选择方案B**：User chose 方案B (offline inline parser, default dual-column). I'll implement now.
> **修改index.html**line 1-34
> **修改script.js** line 1-83

![Cline 实际产出](images/cline-result.png)
---

## 四、注意事项（Notes）

1. **API Key 安全**：Key 不要提交到仓库或公开发到 Issue。本地用环境变量或 WorkBuddy 的密钥管理存储。
2. **模型名称**：一定要根据Openrouter官网显示的模型的名称例如tencent/hy3:free。
3. **如果填了 Key 却报 401 怎么办**:
检查 API Key 是否正确（确保是 sk-... 格式，前后无空格）
确认 API Key 未过期且账户有余额/额度
如果是 OpenRouter，检查 :free 模型是否还有免费调用次数

## 五、小结

通过 OpenAI 兼容协议，cline可在 **5 分钟内** 接入 Hy3。
Hy3 的 256K 上下文 + 稳定工具调用，使其特别适合「分析大型代码库」「长文档处理」
这类 Cline 核心场景。本指南已端到端验证（配置 → 首次对话 → 真实任务跑通）。