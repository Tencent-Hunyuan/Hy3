#!/usr/bin/env bash

set -euo pipefail
set +x

APP_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$APP_ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export HY3_MAX_ROUNDS=${HY3_DEMO_MAX_ROUNDS:-9}
export HY3_MAX_TOKENS=${HY3_DEMO_MAX_TOKENS:-16384}

if [[ -x .venv/bin/hy3-repo-scout ]]; then
  SCOUT=.venv/bin/hy3-repo-scout
elif command -v hy3-repo-scout >/dev/null 2>&1; then
  SCOUT=$(command -v hy3-repo-scout)
else
  printf 'hy3-repo-scout is not installed. See README.md.\n' >&2
  exit 2
fi

if [[ -z "${HY3_API_KEY:-${OPENROUTER_API_KEY:-}}" ]]; then
  printf 'Configure HY3_API_KEY or OPENROUTER_API_KEY before running live demos.\n' >&2
  exit 2
fi

mkdir -p demos/artifacts
IMPACT_REPORT=demos/artifacts/change-impact.md
PIPELINE_REPORT=demos/artifacts/lora-pipeline-audit.md
rm -f "$IMPACT_REPORT" "$PIPELINE_REPORT"

cleanup() {
  status=$?
  trap - EXIT
  if [[ $status -ne 0 ]]; then
    rm -f "$IMPACT_REPORT" "$PIPELINE_REPORT"
  fi
  exit "$status"
}
trap cleanup EXIT

printf '\033[2J\033[H'
printf 'Hy3 Repo Scout | Live demo 1/2 | Reasoning-mode change impact\n\n'
"$SCOUT" --repo ../.. --demo impact \
  --output "$IMPACT_REPORT"

printf '\nHy3 Repo Scout | Live demo 2/2 | LoRA pipeline consistency audit\n\n'
"$SCOUT" --repo ../.. --demo pipeline \
  --output "$PIPELINE_REPORT"

printf '\nBoth live Hy3 demos completed with verified citations.\n'
