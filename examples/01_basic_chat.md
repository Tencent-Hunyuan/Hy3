# 01 · Basic Chat

## 说明

演示 Chat Completions 的单轮问答与多轮对话。

## 运行

```bash
python 01_basic_chat.py
```

## 请求

- 接口：`POST {BASE_URL}/chat/completions`
- `messages` 支持 `system` / `user` / `assistant`
- 多轮时将上一轮 `assistant` 内容写回 `messages`

## 响应字段

```text
resp.choices[0].message.content
resp.usage
resp.model
```

## 示例输出

```text
=== single-turn ===
assistant: 我是混元，是由腾讯开发的大模型，能回答问题、解决问题、学习新知识、创造内容以及进行闲聊。
usage: CompletionUsage(completion_tokens=26, prompt_tokens=19, total_tokens=45, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=0, rejected_prediction_tokens=None), prompt_tokens_details=PromptTokensDetails(audio_tokens=None, cached_tokens=0))

=== multi-turn ===
assistant-1: 好的，小明，我已经记住你的名字了。有什么可以帮你的吗？
assistant-2: 你叫小明。
```
