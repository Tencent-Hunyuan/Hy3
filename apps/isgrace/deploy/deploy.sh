#!/usr/bin/env bash
# Repeatable deploy — run this locally from the repo root for every update.
# Builds the frontend locally (never on the VPS — avoids any Vite-build memory
# risk regardless of the box's specs), then ships only the build artifacts +
# server code. Only ever restarts the `isgrace` service — never touches nginx
# or the existing `athenax-dashboard` (bd.limlamleen.com) service on this box.
# `data/` is never a source or destination here — structurally impossible for
# this script to touch it.

set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_HOST="${DEPLOY_HOST:-43.156.131.187}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/isgrace}"

echo "== Building frontend locally =="
npm run build

echo "== Syncing dist/, server/, src/types/ (server's only cross-boundary import) =="
# rsync only auto-creates the leaf directory, not intermediate parents — src/types/
# needs src/ to exist first, and it won't on a fresh deploy dir.
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "mkdir -p ${DEPLOY_DIR}/src/types"
rsync -avz --delete dist/      "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_DIR}/dist/"
rsync -avz --delete server/    "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_DIR}/server/"
rsync -avz --delete src/types/ "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_DIR}/src/types/"
rsync -avz package.json package-lock.json "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_DIR}/"

echo "== Installing production deps + restarting service =="
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "cd ${DEPLOY_DIR} && npm install --omit=dev && chown -R isgrace:isgrace ${DEPLOY_DIR} && systemctl restart isgrace"

echo "== Done. Checking service status =="
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "systemctl --no-pager status isgrace | head -10"
