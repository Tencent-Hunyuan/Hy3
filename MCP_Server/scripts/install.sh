#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python -m pip install -e .
cp -n .env.example .env 2>/dev/null || true
echo "Hy3 MCP Server installed. Edit MCP_Server/.env or set HY3_* environment variables before use."
