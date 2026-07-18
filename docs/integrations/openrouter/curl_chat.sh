#!/usr/bin/env bash
# 用法：
#   cp .env.example .env   # 填入 OPENROUTER_API_KEY
#   set -a && source .env && set +a
#   bash curl_chat.sh

set -euo pipefail
: "${OPENROUTER_API_KEY:?请先 export OPENROUTER_API_KEY 或 source .env}"
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
