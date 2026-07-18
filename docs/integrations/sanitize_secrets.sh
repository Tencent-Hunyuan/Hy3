#!/usr/bin/env bash
# 提交前脱敏：还原 docs/integrations 下【会入库】配置里的 Key 占位符。
# .env 默认 gitignore，不会入库，本脚本不改动 .env。
#
# 用法（仓库根目录 Hy3/）：
#   bash docs/integrations/sanitize_secrets.sh
#   git add docs/integrations && git commit ...

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

redact_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  sed -i -E \
    -e 's/(apiKey:[[:space:]]*)sk-or-[A-Za-z0-9_-]+/\1sk-or-v1-xxxxxxxx/g' \
    -e 's/(apiKey:[[:space:]]*)sk-[A-Za-z0-9_-]+/\1sk-xxxxxxxx/g' \
    -e 's/("openaiApiKey":[[:space:]]*")sk-or-[A-Za-z0-9_-]+/\1sk-or-v1-xxxxxxxx/g' \
    -e 's/("openaiApiKey":[[:space:]]*")sk-[A-Za-z0-9_-]+/\1sk-xxxxxxxx/g' \
    -e 's/("api_key":[[:space:]]*")sk-or-[A-Za-z0-9_-]+/\1sk-or-v1-xxxxxxxx/g' \
    -e 's/("api_key":[[:space:]]*")sk-[A-Za-z0-9_-]+/\1sk-xxxxxxxx/g' \
    "$f"
}

echo "Sanitizing tracked configs under docs/integrations ..."

for f in \
  "${ROOT}/continue/config.tokenhub.yaml" \
  "${ROOT}/continue/config.openrouter.yaml" \
  "${ROOT}/cursor/settings.openrouter.json" \
  "${ROOT}/cursor/settings.tokenhub.json" \
  "${ROOT}/dify/provider.tokenhub.json" \
  "${ROOT}/dify/provider.openrouter.json"
do
  if [[ -f "$f" ]]; then
    redact_file "$f"
    echo "  cleaned $f"
  fi
done

# 扫描将入库的文本，排除 .env
if grep -RInE 'sk-(or-v1-)?[A-Za-z0-9]{20,}' "$ROOT" \
  --exclude='sanitize_secrets.sh' \
  --exclude='sync_env.sh' \
  --exclude='.env' \
  --exclude-dir='.git' \
  | grep -vE '\.env:' \
  | grep -vE 'sk-xxxxxxxx|sk-or-v1-xxxxxxxx' ; then
  echo
  echo "错误: 仍检测到疑似真实 Key（非 .env）。请检查后重试。" >&2
  exit 1
fi

echo
echo "脱敏完成。.env 未改动（本地密钥保留）。"
echo "  git add docs/integrations && git commit ..."
echo "提交后若 Continue yaml 需要真 Key，再运行: bash docs/integrations/sync_env.sh"
