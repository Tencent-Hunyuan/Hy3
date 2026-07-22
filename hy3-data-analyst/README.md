# hy3-data-analyst

A Python MCP (Model Context Protocol) Server for local data file analysis: explore, summarize, visualize, and AI-powered Q&A. Built with FastMCP, pandas, matplotlib, and Hy3 (via OpenRouter).

[中文文档](README.CN.md)

## Features

- **4 MCP Tools**: `list_data_files`, `stats_summary`, `plot_chart`, `ask_data`
- **Multi-format support**: CSV, JSON, Excel (.xlsx/.xls)
- **AI-powered Q&A**: Integrates with Hy3 (via OpenRouter or Tencent Cloud LKE) for intelligent data analysis
- **Offline mode**: Works without an API key for listing, stats, and plotting
- **Cross-platform**: Windows, Linux, macOS
- **One-click install**: `pip install -e .`

## Verified MCP Clients

This server has been tested with the following MCP clients:

- **CodeBuddy** — full tool support
- **Trae** — full tool support
- **WorkBuddy** (config provided, same protocol)

See [examples/](examples/) for ready-to-use MCP configuration files.

## Requirements

- Python 3.10+
- Dependencies listed in [requirements.txt](requirements.txt)

## Installation

```bash
cd hy3-data-analyst
pip install -e .
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
pip install -e .
```

## Quick Start

### 1. Configure environment variables

**Option A — .env file (recommended):**

```bash
cp .env.example .env
# Edit .env with your API key
```

**Option B — One-liner (quick setup):**

Windows (PowerShell):
```powershell
$env:HY3_API_KEY="your-key"; $env:HY3_BASE_URL="https://openrouter.ai/api/v1"; $env:HY3_MODEL="tencent/hy3:free"
```

Linux/macOS:
```bash
export HY3_API_KEY="your-key" && export HY3_BASE_URL="https://openrouter.ai/api/v1" && export HY3_MODEL="tencent/hy3:free"
```

`.env` file format:

```
HY3_API_KEY=sk-your-key-here
HY3_BASE_URL=https://openrouter.ai/api/v1
HY3_MODEL=tencent/hy3:free
HY3_MCP_ROOT=/path/to/your/data/workspace
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HY3_API_KEY` | Only for `ask_data` | — | Your API key for Hy3/OpenRouter |
| `HY3_BASE_URL` | No | `https://openrouter.ai/api/v1` | API endpoint |
| `HY3_MODEL` | No | `tencent/hy3:free` | Model name |
| `HY3_MCP_ROOT` | No | Current working directory | Workspace root for file access |

### 2. Start the server

```bash
hy3-data-analyst
```

Or directly with Python:

```bash
python -m hy3_data_analyst.server
```

### 3. Connect from an MCP client

See [docs/clients/](docs/clients/) for detailed setup guides:
- [CodeBuddy](docs/clients/codebuddy.md)
- [WorkBuddy](docs/clients/workbuddy.md)
- [Trae](docs/clients/trae.md)

Pre-made config templates (copy to your client's MCP settings):
- [examples/codebuddy.mcp.json](examples/codebuddy.mcp.json)
- [examples/workbuddy.mcp.json](examples/workbuddy.mcp.json)
- [examples/trae.mcp.json](examples/trae.mcp.json)

Each template uses placeholder paths — replace `/absolute/path/to/your/python` and `/absolute/path/to/hy3-data-analyst/.env` with your actual paths before use. Example:

```json
{
  "mcpServers": {
    "hy3-data-analyst": {
      "command": "/path/to/your/python",
      "args": ["-m", "hy3_data_analyst.server"],
      "env": {
        "HY3_ENV_FILE": "/path/to/hy3-data-analyst/.env"
      }
    }
  }
}
```

If you installed via `pip install -e .`, you can also use the CLI entry point:

```json
{
  "mcpServers": {
    "hy3-data-analyst": {
      "command": "hy3-data-analyst",
      "args": [],
      "env": {
        "HY3_ENV_FILE": "/path/to/hy3-data-analyst/.env"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `list_data_files` | List CSV/JSON/Excel files under a directory |
| `stats_summary` | Generate statistical summary (shape, missing values, numeric stats, top categories) |
| `plot_chart` | Draw line/bar/scatter/histogram charts and save as PNG |
| `ask_data` | Ask natural language questions about the data (requires Hy3 API key) |

## Typical Workflow

A typical conversation with the AI client:

1. **List files**: "What data files do I have?"
   → `list_data_files` returns available files

2. **Get statistics**: "Show me a summary of sales.csv"
   → `stats_summary` returns shape, missing values, numeric stats, categories

3. **Plot chart**: "Plot a bar chart of sales by region"
   → `plot_chart` generates a PNG and returns the path with trend analysis

4. **Ask questions**: "Which region had the highest revenue and why?"
   → `ask_data` calls Hy3 for AI-powered analysis

## Usage Examples

### List data files

```
Tool: list_data_files
Args: {"path": "."}
→ Lists all .csv, .json, .xlsx, .xls files in the workspace
```

### Get statistics

```
Tool: stats_summary
Args: {"file_path": "examples/sales.csv"}
→ Returns Markdown stats: shape, missing values, numeric summaries, category counts
```

### Plot a chart

```
Tool: plot_chart
Args: {
  "file_path": "examples/sales.csv",
  "x_column": "日期",
  "y_column": "销量",
  "chart_type": "line",
  "title": "Sales Trend"
}
→ Saves chart to charts/ directory, returns path and trend analysis
```

### Ask a question

```
Tool: ask_data
Args: {"file_path": "examples/sales.csv", "question": "Which region has the highest total sales?"}
→ Calls Hy3 API with data context, returns AI-generated answer
```

## Offline Mode

`list_data_files`, `stats_summary`, and `plot_chart` work **without** an API key. Only `ask_data` requires `HY3_API_KEY`. If unset, `ask_data` returns a clear error message instead of crashing.

## Testing

```bash
pip install -e ".[dev]"
pytest tests/
```

### Protocol verification (no GUI needed)

```bash
python stdio_client.py
```

This launches the server as a subprocess and validates the MCP JSON-RPC protocol.

## Demo

See [demo/README.md](demo/README.md) for a description of the demonstration video showing the full workflow across multiple MCP clients.

## Project Structure

```
hy3-data-analyst/
├── src/hy3_data_analyst/
│   ├── __init__.py
│   ├── server.py          # Main entry point
│   ├── config.py          # Env var loading & validation
│   ├── data_utils.py      # Safe file I/O
│   ├── stats.py           # Statistical summary
│   ├── plot.py            # Chart plotting
│   ├── hy3_client.py      # Hy3 API client
│   └── tools.py           # MCP tool registration
├── tests/                 # pytest test suite
├── examples/              # Sample data & MCP configs
├── docs/clients/          # Client setup guides
├── demo/                  # Demo video placeholder
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Package metadata & install config
├── stdio_client.py        # Protocol test client
├── .env.example           # Environment variable template
└── .gitignore
```

## License

MIT — see [LICENSE](LICENSE).
