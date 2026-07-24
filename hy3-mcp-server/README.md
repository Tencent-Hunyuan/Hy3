<p align="left">
    <a href="README_CN.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Hy3 Knowledge Base MCP Server

An MCP (Model Context Protocol) Server that provides **Knowledge Base Q&A** capabilities powered by [Tencent Hunyuan Hy3](https://github.com/Tencent-Hunyuan/Hy3) — a 295B MoE model with 21B active parameters.

This server enables any MCP-compatible client (CodeBuddy, WorkBuddy, Cursor, Cline, etc.) to read local documents and ask Hy3 questions about their content — no extra development needed.

## Features

- **Document Reading** — Supports `.txt`, `.md`, `.csv`, `.json`, `.py`, `.pdf`, `.docx`, and more
- **Knowledge Base Q&A** — Ask questions about document content, with Hy3 providing grounded answers
- **Smart Summarization** — Generate comprehensive, brief, or bullet-point summaries of any document
- **Directory Search & Answer** — Scan directories for relevant files and answer queries based on their content
- **Web Search & Answer** — Search the web for up-to-date information and get Hy3-powered answers
- **Document Comparison** — Compare multiple documents to find differences, agreements, or contradictions

## Quick Start

### 1. Prerequisites

- Python 3.10+
- A valid Hy3 API Key (from [Tencent Cloud TokenHub](https://cloud.tencent.com/product/hunyuan))
- (Optional) A Tavily API Key for web search (get a free key at [https://tavily.com](https://tavily.com))

### 2. Install

```bash
# Clone the repository
git clone -b rhinobird2026 https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3

# Navigate to the MCP server package
cd hy3-mcp-server

# Create a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install as an editable package (so `python -m hy3_mcp_server.server` works)
pip install -e .
```

### 3. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env
```

Edit `.env` and set your API key:

```
HY3_API_KEY=your_actual_api_key_here
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
TAVILY_API_KEY=your_tavily_api_key_here
```

> **Important:** Never hardcode your API key in source code. Always use environment variables.

### 4. Run the Server

```bash
# Method 1: Run directly with the package entry point (after pip install -e .)
hy3-mcp-server

# Method 2: Run as a Python module
python -m hy3_mcp_server.server
```

## MCP Client Configuration

### CodeBuddy / WorkBuddy (Project-level)

First, install the package in your Python environment:

```bash
cd /path/to/hy3-mcp-server
pip install -e .
```

Then add a `.mcp.json` file in your project root:

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "env": {
        "HY3_API_KEY": "your_api_key_here",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3",
        "TAVILY_API_KEY": "your_tavily_api_key_here"
      }
    }
  }
}
```

Or use the CLI to add:

```bash
# CodeBuddy
codebuddy mcp add hy3-knowledge-base -- python -m hy3_mcp_server.server

# WorkBuddy
workbuddy mcp add hy3-knowledge-base -- python -m hy3_mcp_server.server
```

### Cursor

Add to your Cursor MCP settings (`Settings > MCP`):

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "env": {
        "HY3_API_KEY": "your_api_key_here",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3",
        "TAVILY_API_KEY": "your_tavily_api_key_here"
      }
    }
  }
}
```

### Cline

Add to `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "hy3-knowledge-base": {
      "command": "python",
      "args": ["-m", "hy3_mcp_server.server"],
      "env": {
        "HY3_API_KEY": "your_api_key_here",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3",
        "TAVILY_API_KEY": "your_tavily_api_key_here"
      }
    }
  }
}
```

## Tools

### 1. `read_file`

Read and extract text content from a local file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | string | Yes | Path to the file to read |
| `max_chars` | integer | No | Maximum characters to return (default: 50000) |

**Example usage in MCP client:**
> "Read the file ./docs/architecture.md"

### 2. `ask_about_documents`

Ask a question about the content of one or more documents, answered by Hy3.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_paths` | array[string] | Yes | List of file paths to read as context |
| `question` | string | Yes | The question to ask |
| `reasoning_effort` | string | No | "no_think", "low", or "high" (default: "high") |

**Example usage in MCP client:**
> "Based on ./src/main.py and ./README.md, what is the architecture of this project?"

### 3. `summarize_document`

Summarize a document using Hy3 with customizable style.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | string | Yes | Path to the document |
| `summary_type` | string | No | "comprehensive", "brief", or "bullet" (default: "comprehensive") |
| `max_length` | integer | No | Target word count (default: 500) |

**Example usage in MCP client:**
> "Summarize ./report.pdf in bullet points"

### 4. `search_files_and_answer`

Search for files in a directory and answer a question based on their content.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `directory` | string | Yes | Directory path to search in |
| `query` | string | Yes | The question or topic to search for |
| `file_pattern` | string | No | Glob pattern (e.g., "*.py", "*.md") (default: "*") |
| `max_files` | integer | No | Maximum files to read (default: 10) |

**Example usage in MCP client:**
> "Search the ./src directory and tell me how authentication works"

### 5. `web_search_and_answer`

Search the web using Tavily Search API, then use Hy3 to answer.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | The search query |
| `max_results` | integer | No | Maximum number of search results (default: 5) |
| `reasoning_effort` | string | No | "no_think", "low", or "high" (default: "high") |

**Example usage in MCP client:**
> "Search the web for the latest Python 3.13 features and explain them"

### 6. `compare_documents`

Compare two or more documents and analyze differences using Hy3.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_paths` | array[string] | Yes | List of file paths to compare (minimum 2) |
| `aspect` | string | No | "general", "differences", "agreements", or "contradictions" (default: "general") |
| `reasoning_effort` | string | No | "no_think", "low", or "high" (default: "high") |

**Example usage in MCP client:**
> "Compare ./docs/v1_spec.md and ./docs/v2_spec.md and highlight the differences"

## Architecture

```
┌─────────────────────┐
│   MCP Client        │
│ (Cursor / Cline /   │
│  CodeBuddy / ...)   │
└─────────┬───────────┘
          │ MCP Protocol (stdio)
          ▼
┌─────────────────────┐
│  hy3-mcp-server     │
│  ┌───────────────┐  │
│  │  FastMCP      │  │
│  │  (MCP Layer)  │  │
│  └───────┬───────┘  │
│  ┌───────┴───────┐  │
│  │ Tool Handlers │  │
│  │ • read_file   │  │
│  │ • ask_about_  │  │
│  │   documents   │  │
│  │ • summarize_  │  │
│  │   document    │  │
│  │ • search_     │  │
│  │   files_and_  │  │
│  │   answer      │  │
│  │ • web_search_ │  │
│  │   and_answer  │  │
│  │ • compare_    │  │
│  │   documents   │  │
│  └───────┬───────┘  │
│  ┌───────┴───────┐  │
│  │ hy3_client    │  │──▶ Hy3 API (OpenAI-compatible)
│  │ (API Layer)   │  │    tokenhub.tencentmaas.com
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ web_search    │  │──▶ Tavily Search API
│  │ (Search Layer)│  │    tavily.com
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ File Parsers  │  │──▶ Local Filesystem
│  │ • Text/PDF/   │  │
│  │   DOCX/Code   │  │
│  └───────────────┘  │
└─────────────────────┘
```

## Verification

This server has been verified to work with the following MCP clients:

1. **Cursor** — Add via Settings > MCP, tools appear in agent mode
2. **Cline** — Add to `cline_mcp_settings.json`, tools accessible in chat

To verify yourself:
1. Configure the server in your MCP client
2. Ask: "Read the file ./README.md and summarize it"
3. The client should call `read_file` then `summarize_document`

You should see 6 tools available: `read_file`, `ask_about_documents`, `summarize_document`, `search_files_and_answer`, `web_search_and_answer`, and `compare_documents`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HY3_API_KEY` | Yes | — | Your Hy3 API key |
| `HY3_BASE_URL` | No | `https://tokenhub.tencentmaas.com/v1` | API base URL |
| `HY3_MODEL` | No | `hy3` | Model name to use |
| `TAVILY_API_KEY` | No | — | Your Tavily API key (needed for `web_search_and_answer`) |

## License

Apache License 2.0 — same as [Hy3](https://github.com/Tencent-Hunyuan/Hy3)
