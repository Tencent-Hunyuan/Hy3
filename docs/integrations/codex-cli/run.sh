#!/usr/bin/env bash
# 一键加载 Key 并启动 Codex（仓库根目录 Hy3/ 或任意目录均可）
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
ENV_FILE="${REPO}/docs/integrations/codex-cli/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "缺少 $ENV_FILE ，请先: bash docs/integrations/sync_env.sh" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
if [[ -z "${HY3_API_KEY:-}" || "${HY3_API_KEY}" == sk-xxxxxxxx ]]; then
  echo "HY3_API_KEY 未配置，请编辑 docs/integrations/.env 后运行 sync_env.sh" >&2
  exit 1
fi
cd "$REPO"
exec codex "$@"
