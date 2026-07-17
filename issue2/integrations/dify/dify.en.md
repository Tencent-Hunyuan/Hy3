# Using Hy3 with Dify

> 🌐 中文版本： [dify.md](dify.md)

## Introduction

[Dify](https://dify.ai) is an open-source LLM application development platform that supports visual orchestration of AI workflows, RAG knowledge bases, and Agent tool calling. As a low-code platform, Dify has built-in support for **OpenAI-compatible APIs**, so Hy3 integrates seamlessly.

## Use Cases

- Low-code building of Hy3-powered ChatBots / customer-service systems
- Hy3-based content generation pipelines (batch writing, translation, summarization)
- RAG knowledge-base Q&A (Hy3 long context + knowledge-base retrieval augmentation)
- Multi-step Agent workflows (Hy3 reasoning + tool calling + conditional branching)

## Requirements

| Item | Requirement |
|:---|:---|
| Dify version | ≥ 0.6.0 (community or cloud edition) |
| Deployment | Docker Compose (recommended) or Dify Cloud |
| Hy3 service | Self-hosted OpenAI-compatible API endpoint |

## Configuration

### Step 1: Add the Hy3 model provider

1. Log in to Dify → top-right avatar → **Settings** → **Model Providers**
2. Find **OpenAI-API-compatible** → click **Add Model**
3. Fill in the configuration:

```
Model Name:            hy3
Model Type:            LLM
API Endpoint URL:      https://tokenhub.tencentmaas.com/v1
API Key:               your-api-key
Model Name (API param): hy3
```

4. Click **Save**; Dify will automatically test the connection.

### Step 2: Select Hy3 in your app

Create or edit an app → **Model Settings** → choose `OpenAI-API-compatible` → `hy3`

### Key parameter mapping

| Hy3 param | Dify config |
|:---|:---|
| `temperature=0.9` | App → Model Params → set Temperature to `0.9` |
| `top_p=1.0` | App → Model Params → set Top P to `1.0` |
| `reasoning_effort` | Pass via **custom model parameters** (advanced settings) |
| `max_tokens` | App → Model Params → Max Tokens |
| Function Call | Dify converts it to tool calls automatically |

### Passing Hy3-specific parameters

In Dify's model provider config, add custom parameters:

```json
{
  "chat_template_kwargs": {
    "reasoning_effort": "high"
  }
}
```

## End-to-End Demos

### Demo 1: A Hy3-powered technical documentation assistant (RAG workflow)

**Scenario**: Build a ChatBot with Hy3 that answers questions about internal technical docs.

#### Workflow design

```
[User Input]
    │
    ▼
[Knowledge Retrieval] ── retrieve relevant content from uploaded markdown/pdf docs
    │
    ▼
[Hy3 LLM Node] ── generate an answer based on retrieval results + the user question
    │
    ▼
[Output]
```

#### Dify node config

**Knowledge retrieval node**:
```
Knowledge base: select the uploaded technical docs
Retrieval settings: TopK=5, similarity threshold=0.7
```

**Hy3 LLM node prompt**:

```
You are a technical documentation assistant. Answer the user's question based on the following knowledge-base retrieval results.

**Knowledge base content**:
{{#context#}}

**User question**:
{{#query#}}

**Answering requirements**:
1. Prioritize information from the knowledge base; do not fabricate
2. If the knowledge base has no relevant info, tell the user clearly
3. For code, use markdown code-block format
4. Keep answers concise, accurate, and well-organized
```

#### Test result

```
User: What reasoning modes does Hy3 have?
Assistant: According to the docs, Hy3 supports three reasoning modes, controlled by the reasoning_effort parameter:
- "no_think": direct reply, good for everyday conversation
- "low": light reasoning
- "high": deep chain-of-thought, good for complex tasks like math and coding
It's recommended to use temperature=0.9, top_p=1.0 on the command line.
```

### Demo 2: Hy3 Agent — Code review + auto-create Issue

**Workflow design**:

```
[Trigger: GitHub Webhook]
    │
    ▼
[Read PR content]
    │
    ▼
[Hy3 Agent Node] ── review the code
    │           │
    │           └── [Tool: GitHub API - create Issue]
    │           └── [Tool: GitHub API - add Comment]
    │
    ▼
[Conditional branch] ── review passed? ── Yes ──> [Auto Approve]
            │
            └── No ──> [Create Issue + Notify]
```

**Hy3 Agent system prompt**:

```
You are a code review Agent. Your tasks are:
1. Check whether the code style follows the project conventions
2. Identify potential security vulnerabilities (SQL injection, XSS, etc.)
3. Assess performance impact
4. If issues are found, use the create_issue tool to create a GitHub Issue
5. Use the add_comment tool to add review comments under the PR

Available tools:
- create_issue(title, body, labels): create a GitHub Issue
- add_comment(pr_number, body): add a comment under the PR
- approve_pr(pr_number): approve the PR
```

### Demo 3: Batch content generation pipeline

**Scenario**: Upload a CSV keyword list; Hy3 generates SEO articles in batch.

```
[CSV Import] ── read the keyword list
    │
    ▼
[Iterator] ── process one by one
    │
    ▼
[Hy3 LLM Node]
    │  Prompt: "Write an 800-word technical article around the keyword {{keyword}}"
    ▼
[Code Node] ── format + add metadata
    │
    ▼
[Output: list of Markdown files]
```

## Common Notes

| Issue | Cause | Solution |
|:---|:---|:---|
| Connection test fails | Network unreachable or wrong endpoint format | Check whether `base_url` ends with `/v1` |
| Agent tool calling fails | Hy3 tool-call format incompatible with Dify | Ensure the Hy3 service was deployed with `--tool-call-parser hy_v3` (vLLM) |
| Empty knowledge retrieval | Docs not properly chunked/indexed | Check doc format and adjust chunking parameters |
| Unstable content quality | Improper Temperature | Lower to `0.7-0.8` for content generation, keep `0.9` for creative work |
| `reasoning_effort` has no effect | Dify didn't pass the custom param | Add an `extra_body` parameter in the model provider config |
| Workflow execution timeout | Hy3 Agent reasoning takes too long | Increase the Dify workflow timeout, or use `reasoning_effort=low` |


[← Back to Index](../README.en.md)
