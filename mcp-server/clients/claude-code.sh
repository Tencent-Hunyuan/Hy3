#!/usr/bin/env bash
# Copyright 2026 Tencent Inc. All Rights Reserved.
# Licensed under the Apache License, Version 2.0.
#
# Register hy3-mcp with MCP CLI clients (run from anywhere; edit the paths).
# 注册 hy3-mcp 到 CLI 类 MCP 客户端(按需修改路径后执行)。
#
# All keys come from YOUR environment — nothing is hardcoded here.
# 所有密钥来自你自己的环境变量,本文件不含任何密钥。

MCP_SERVER_DIR=/ABS/PATH/TO/Hy3/mcp-server   # <- edit me 改成你的绝对路径

# ---------------- Claude Code (verified on the dev machine, offline mode) ---
# 真实后端 real backend:
claude mcp add hy3 \
  -e HY3_API_BASE="${HY3_API_BASE:-http://127.0.0.1:8000/v1}" \
  -e HY3_API_KEY="${HY3_API_KEY}" \
  -e HY3_MCP_ROOT="$PWD" \
  -- uvx --from "$MCP_SERVER_DIR" hy3-mcp

# 离线试玩(无需任何 key) offline demo (no key needed):
#   claude mcp add hy3-offline -e HY3_MCP_OFFLINE=1 -e HY3_MCP_ROOT="$PWD" \
#     -- uvx --from "$MCP_SERVER_DIR" hy3-mcp
# 单次调用验证 one-shot verification:
#   claude -p "Call the hy3_status tool and report mode and model." \
#     --allowedTools "mcp__hy3__hy3_status" --max-turns 3

# ---------------- CodeBuddy Code CLI (同构命令 same shape) ------------------
#   codebuddy mcp add hy3 \
#     -e HY3_API_BASE="${HY3_API_BASE:-http://127.0.0.1:8000/v1}" \
#     -e HY3_API_KEY="${HY3_API_KEY}" \
#     -e HY3_MCP_ROOT="$PWD" \
#     -- uvx --from "$MCP_SERVER_DIR" hy3-mcp
# GUI 用户请改用项目级配置 clients/codebuddy.mcp.json。
