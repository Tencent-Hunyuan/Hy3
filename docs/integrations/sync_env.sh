#!/usr/bin/env bash
# 将 docs/integrations/.env 同步到各工具子目录的 .env
# 用法（在仓库根目录 Hy3/ 下执行）：
#   cp docs/integrations/.env.example docs/integrations/.env
#   bash docs/integrations/sync_env.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="${ROOT}/.env"

if [[ ! -f "$SRC" ]]; then
  echo "缺少 ${SRC}"
  echo "请先（在 Hy3 根目录）: cp docs/integrations/.env.example docs/integrations/.env"
  echo "填入真实 Key 后: bash docs/integrations/sync_env.sh"
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$SRC"
set +a

require() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "警告: ${name} 未设置"
  fi
}

require HY3_API_KEY
require OPENROUTER_API_KEY

write_env() {
  local dest="$1"
  shift
  mkdir -p "$(dirname "$dest")"
  {
    echo "# 由 docs/integrations/sync_env.sh 自动生成 — 勿手改后期望持久化"
    echo "# 请编辑 docs/integrations/.env 后重新运行: bash docs/integrations/sync_env.sh"
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

if [[ -n "${HY3_API_KEY:-}" && "${HY3_API_KEY}" != sk-xxxxxxxx ]]; then
  sed "s|apiKey: sk-xxxxxxxx|apiKey: ${HY3_API_KEY}|" \
    "${ROOT}/continue/config.tokenhub.yaml.example" \
    >"${ROOT}/continue/config.tokenhub.yaml"
  echo "wrote ${ROOT}/continue/config.tokenhub.yaml"
fi

if [[ -n "${OPENROUTER_API_KEY:-}" && "${OPENROUTER_API_KEY}" != sk-or-v1-xxxxxxxx ]]; then
  sed "s|apiKey: sk-or-v1-xxxxxxxx|apiKey: ${OPENROUTER_API_KEY}|" \
    "${ROOT}/continue/config.openrouter.yaml.example" \
    >"${ROOT}/continue/config.openrouter.yaml"
  echo "wrote ${ROOT}/continue/config.openrouter.yaml"
fi

cp "${ROOT}/codex-cli/config.tokenhub.toml.example" "${ROOT}/codex-cli/config.tokenhub.toml"
cp "${ROOT}/codex-cli/config.openrouter.toml.example" "${ROOT}/codex-cli/config.openrouter.toml"
echo "wrote ${ROOT}/codex-cli/config.tokenhub.toml"
echo "wrote ${ROOT}/codex-cli/config.openrouter.toml"

echo
echo "完成。各子目录 .env 已与 ${SRC} 对齐。"
echo "Codex 示例（在 Hy3 根目录）:"
echo "  set -a && source docs/integrations/codex-cli/.env && set +a"
echo "  cp docs/integrations/codex-cli/config.tokenhub.toml ~/.codex/config.toml"
