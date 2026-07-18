#!/usr/bin/env bash
# 将 docs/integrations/.env 同步到各工具子目录，并按需注入本地配置中的 Key。
# 用法（仓库根目录 Hy3/）：
#   bash docs/integrations/sync_env.sh
# 提交前请运行：bash docs/integrations/sanitize_secrets.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="${ROOT}/.env"

if [[ ! -f "$SRC" ]]; then
  cat >"$SRC" <<'EOF'
# 本地密钥（勿提交；commit 前运行 sanitize_secrets.sh）
HY3_API_KEY=sk-xxxxxxxx
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=tencent/hy3
EOF
  echo "已创建 ${SRC}，请填入真实 Key 后重新运行本脚本。"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$SRC"
set +a

write_env() {
  local dest="$1"
  shift
  {
    echo "# 由 sync_env.sh 生成。提交前请运行: bash docs/integrations/sanitize_secrets.sh"
    echo "#"
    local key
    for key in "$@"; do
      printf '%s=%s\n' "$key" "${!key-}"
    done
  } >"$dest"
  echo "wrote $dest"
}

write_env "${ROOT}/openrouter/.env" \
  OPENROUTER_API_KEY OPENROUTER_BASE_URL OPENROUTER_MODEL

write_env "${ROOT}/cursor/.env" \
  OPENROUTER_API_KEY OPENROUTER_BASE_URL OPENROUTER_MODEL \
  HY3_API_KEY HY3_BASE_URL HY3_MODEL

write_env "${ROOT}/workbuddy/.env" \
  OPENROUTER_API_KEY OPENROUTER_BASE_URL OPENROUTER_MODEL \
  HY3_API_KEY HY3_BASE_URL HY3_MODEL

write_env "${ROOT}/codex-cli/.env" \
  OPENROUTER_API_KEY HY3_API_KEY HY3_BASE_URL HY3_MODEL

write_env "${ROOT}/dify/.env" \
  HY3_API_KEY OPENROUTER_API_KEY

# 注入 WorkBuddy 对照 JSON 中的 apiKey（仅本地；提交前 sanitize）
inject_json_key() {
  local file="$1"
  local placeholder="$2"
  local value="$3"
  [[ -f "$file" ]] || return 0
  if [[ -n "$value" && "$value" != "$placeholder" ]]; then
    python3 - "$file" "$placeholder" "$value" <<'PY'
import json, sys
path, placeholder, value = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
if data.get("apiKey") in (None, "", placeholder) or str(data.get("apiKey", "")).startswith("sk-"):
    data["apiKey"] = value
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"updated {path} (local key)")
PY
  fi
}

inject_json_key "${ROOT}/workbuddy/settings.tokenhub.json" "sk-xxxxxxxx" "${HY3_API_KEY:-}"
inject_json_key "${ROOT}/workbuddy/settings.openrouter.json" "sk-or-v1-xxxxxxxx" "${OPENROUTER_API_KEY:-}"

echo
echo "完成。WorkBuddy：按 docs/integrations/workbuddy/settings.tokenhub.json 在客户端填写。"
echo "Codex：bash docs/integrations/codex-cli/run.sh \"你的问题\""
