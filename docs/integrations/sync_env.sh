#!/usr/bin/env bash
# 将 docs/integrations/.env 同步到各工具子目录，并按需注入本地配置中的 Key。
# 用法（仓库根目录 Hy3/）：
#   # 若尚无 .env，先创建并填写 Key
#   bash docs/integrations/sync_env.sh
#
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

write_env "${ROOT}/continue/.env" \
  OPENROUTER_API_KEY OPENROUTER_BASE_URL OPENROUTER_MODEL \
  HY3_API_KEY HY3_BASE_URL HY3_MODEL

write_env "${ROOT}/codex-cli/.env" \
  OPENROUTER_API_KEY HY3_API_KEY HY3_BASE_URL HY3_MODEL

write_env "${ROOT}/dify/.env" \
  HY3_API_KEY OPENROUTER_API_KEY

# 注入 Continue yaml 中的 apiKey（本地使用；提交前会被 sanitize 还原）
if [[ -n "${HY3_API_KEY:-}" && "${HY3_API_KEY}" != sk-xxxxxxxx ]]; then
  sed -i "s|^\\([[:space:]]*apiKey: \\).*|\\1${HY3_API_KEY}|" \
    "${ROOT}/continue/config.tokenhub.yaml"
  echo "updated ${ROOT}/continue/config.tokenhub.yaml (local key)"
fi

if [[ -n "${OPENROUTER_API_KEY:-}" && "${OPENROUTER_API_KEY}" != sk-or-v1-xxxxxxxx ]]; then
  sed -i "s|^\\([[:space:]]*apiKey: \\).*|\\1${OPENROUTER_API_KEY}|" \
    "${ROOT}/continue/config.openrouter.yaml"
  echo "updated ${ROOT}/continue/config.openrouter.yaml (local key)"
fi

echo
echo "完成。Codex（在 Hy3 根目录）:"
echo "  set -a && source docs/integrations/codex-cli/.env && set +a"
echo "  cp docs/integrations/codex-cli/config.tokenhub.toml ~/.codex/config.toml"
echo "  bash docs/integrations/codex-cli/run.sh \"你的问题\""
