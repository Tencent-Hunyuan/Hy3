#!/usr/bin/env bash
# 用法（在仓库根目录 Hy3/）：
#   bash docs/integrations/sync_env.sh
#   bash docs/integrations/openrouter/curl_chat.sh

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "${DIR}/.env" ]]; then
  set -a && source "${DIR}/.env" && set +a
elif [[ -f "${DIR}/../.env" ]]; then
  set -a && source "${DIR}/../.env" && set +a
fi

: "${OPENROUTER_API_KEY:?请先配置 docs/integrations/.env 并运行 bash docs/integrations/sync_env.sh}"
BASE_URL="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
MODEL="${OPENROUTER_MODEL:-tencent/hy3}"

curl -sS "${BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"用一句话介绍 Hy3。\"}]
  }"
echo
