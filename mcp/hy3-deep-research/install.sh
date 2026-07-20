#!/usr/bin/env bash
# One-click install (venv). ASCII-only messages.
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
    echo "ERROR: python3/python not found (need >= 3.10)" >&2
    exit 1
  fi
fi

PY_VER="$("$PYTHON_BIN" -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "ERROR: need Python >= 3.10, got $PY_VER" >&2
  exit 1
}

echo "==> $PYTHON_BIN ($PY_VER) | $ROOT"
if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
PY="$ROOT/.venv/bin/python"
PIP="$ROOT/.venv/bin/pip"

"$PIP" install -U pip setuptools wheel >/dev/null
"$PIP" install -r "$ROOT/requirements.txt"
"$PIP" install -e "$ROOT" >/dev/null

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

GEN_DIR="$ROOT/configs/generated"
mkdir -p "$GEN_DIR"
SERVER_PY="$ROOT/server.py"
VENV_PY="$ROOT/.venv/bin/python"

cat > "$GEN_DIR/mcp.json" <<EOF
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

"$PY" -c "import server; print('ok', server.mcp.name)"
echo "Done. Set HY3_API_KEY in configs/generated/mcp.json env, paste into Cursor/WorkBuddy."
