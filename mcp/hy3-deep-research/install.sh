#!/usr/bin/env bash
# Hy3 Deep Research MCP — 一键安装（本地 venv，不发布到 PyPI）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "错误：未找到 python3/python，请先安装 Python ≥ 3.10" >&2
    exit 1
  fi
fi

PY_VER="$("$PYTHON_BIN" -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "错误：需要 Python ≥ 3.10，当前为 $PY_VER ($PYTHON_BIN)" >&2
  exit 1
}

echo "==> 使用解释器: $PYTHON_BIN ($PY_VER)"
echo "==> 项目目录: $ROOT"

if [[ ! -d .venv ]]; then
  echo "==> 创建虚拟环境 .venv"
  "$PYTHON_BIN" -m venv .venv
else
  echo "==> 复用已有 .venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
PY="$ROOT/.venv/bin/python"
PIP="$ROOT/.venv/bin/pip"

echo "==> 升级 pip / setuptools / wheel"
"$PIP" install -U pip setuptools wheel >/dev/null

echo "==> 安装依赖 (requirements.txt)"
"$PIP" install -r "$ROOT/requirements.txt"

echo "==> 可编辑安装本包 (entry: hy3-deep-research-mcp)"
"$PIP" install -e "$ROOT" >/dev/null

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "==> 已生成 .env（请填入 HY3_API_KEY，或只在 MCP 客户端 env 中配置）"
else
  echo "==> 保留已有 .env"
fi

# 生成带绝对路径的客户端配置片段（不含真实 Key）
GEN_DIR="$ROOT/configs/generated"
mkdir -p "$GEN_DIR"
SERVER_PY="$ROOT/server.py"
VENV_PY="$ROOT/.venv/bin/python"

cat > "$GEN_DIR/cursor.mcp.json" <<EOF
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "${VENV_PY}",
      "args": ["${SERVER_PY}"],
      "env": {
        "HY3_API_KEY": "sk-xxxxxxxx",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3"
      }
    }
  }
}
EOF

cp "$GEN_DIR/cursor.mcp.json" "$GEN_DIR/workbuddy.mcp.json"

echo "==> 冒烟：import server"
"$PY" -c "import server; print('ok', server.mcp.name)"
echo "完成。编辑 .env 填 Key，再用 configs/generated/*.mcp.json 配客户端。"
