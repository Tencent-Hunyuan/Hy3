#!/usr/bin/env bash
# 一键安装脚本（Linux / macOS / Git Bash）
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python

echo "[1/3] 创建虚拟环境 .venv ..."
"$PYTHON" -m venv .venv

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
else
  source .venv/Scripts/activate   # Git Bash on Windows
fi

echo "[2/3] 安装依赖 ..."
python -m pip install --upgrade pip >/dev/null 2>&1 || echo "  (跳过 pip 自升级)"
python -m pip install mcp "openai>=1.40.0" pandas python-dotenv

echo "[3/3] 准备 .env ..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  已生成 .env，请填入 HY3_API_KEY"
else
  echo "  .env 已存在，跳过"
fi

echo ""
echo "安装完成。连通性自测："
echo "  PYTHONPATH=src python scripts/smoke_test.py"
