# Using Hy3 in Popular AI Products & Tools

This guide shows how to connect Hy3 to mainstream AI clients and platforms, and includes a small showcase application built with Hy3.

## Prerequisites

Deploy Hy3 first (see [main README](../../README.md#deployment)):

```bash
# vLLM (recommended for production)
vllm serve tencent/Hy3 --tensor-parallel-size 8

# SGLang (alternative)
python -m sglang.launch_server --model-path tencent/Hy3 --tp 8
```

Both expose an OpenAI-compatible endpoint at `http://localhost:8000/v1`.

---

## 1. Claude Code (Anthropic CLI)

Claude Code supports [custom model endpoints](https://docs.anthropic.com/en/docs/claude-code/settings) via the `ANTHROPIC_BASE_URL` override, but Hy3 is an OpenAI-compatible API, not Anthropic. Use the MCP Server approach instead:

```bash
# Install the Hy3 MCP server (in this repo)
pip install -e ../../mcp-server

# Register with Claude Code
claude mcp add hy3-research -- python -m hy3_mcp
```

Claude Code can now call `search_web`, `analyze_with_hy3`, and `generate_report` tools backed by your local Hy3 instance.

---

## 2. Cursor

Cursor supports [custom OpenAI-compatible endpoints](https://docs.cursor.com/advanced/models#custom-openai-compatible-models) in **Settings → Models → Add Model**:

| Field | Value |
|-------|-------|
| Model name | `hy3` |
| Base URL | `http://localhost:8000/v1` |
| API Key | `EMPTY` |

After adding, select `hy3` from the model dropdown in the chat panel.

**Tip**: Hy3 shines for complex reasoning tasks. Set `temperature=0.9` and use prompts that benefit from chain-of-thought (`reasoning_effort: "high"` can be enabled by adding `extra_body` if Cursor exposes it, otherwise the model defaults to `no_think`).

---

## 3. Open WebUI

Open WebUI natively supports OpenAI-compatible backends:

```bash
# Start Open WebUI pointing at Hy3
docker run -d -p 3000:8080 \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:8000/v1 \
  -e OPENAI_API_KEY=EMPTY \
  ghcr.io/open-webui/open-webui:main
```

Then open `http://localhost:3000`, sign in, and select `hy3` from the model dropdown.

For **reasoning mode**, add a system prompt:
```
You are Hy3. For complex questions, reason step by step before answering.
```

---

## 4. LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",
    model="hy3",
    temperature=0.9,
    model_kwargs={"extra_body": {"chat_template_kwargs": {"reasoning_effort": "no_think"}}},
)

response = llm.invoke("Summarise the key findings of the 2025 AI Safety Report.")
print(response.content)
```

For agents and chains, Hy3's strong instruction-following makes it a drop-in replacement for GPT-4-class models.

---

## 5. LlamaIndex

```python
from llama_index.llms.openai import OpenAI

llm = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",
    model="hy3",
    temperature=0.9,
)

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
docs = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(docs, llm=llm)
query_engine = index.as_query_engine()
print(query_engine.query("What are the main themes?"))
```

---

## Showcase: CLI Research Assistant

`research_cli.py` is a minimal terminal application that uses Hy3 to do multi-step research:

1. Accept a research question from the user
2. Search the web for relevant sources
3. Analyse each source with Hy3
4. Synthesise a final Markdown report

```bash
pip install openai httpx
python research_cli.py "What are the latest advances in MoE model efficiency?"
```

See [`research_cli.py`](./research_cli.py) for the full implementation.
