#!/usr/bin/env bash
# One-time server setup for isgrace.limlamleen.com on 43.156.131.187 — a server
# that ALREADY runs bd.limlamleen.com via nginx (athenax-dashboard). This script
# only ADDS a new nginx site and a new systemd service; it never touches the
# existing site config, never restarts nginx (reload only), and never changes
# firewall rules (deliberately — see notes at the bottom). Run as root.
#
# Usage:
#   scp deploy/bootstrap.sh deploy/isgrace.service deploy/nginx-isgrace.conf root@43.156.131.187:/root/
#   ssh root@43.156.131.187
#   bash bootstrap.sh

set -euo pipefail

echo "== Installing Node LTS (skipped if already present) =="
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
  apt-get install -y nodejs
fi
node -v

echo "== Creating isgrace system user + app directory (separate from the dashboard app) =="
id -u isgrace >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin isgrace
mkdir -p /opt/isgrace/data
chown -R isgrace:isgrace /opt/isgrace

echo "== Installing systemd unit =="
cp /root/isgrace.service /etc/systemd/system/isgrace.service
systemctl daemon-reload

echo "== Installing nginx site (new file only — does not touch sites-available/athenax-dashboard) =="
cp /root/nginx-isgrace.conf /etc/nginx/sites-available/isgrace
ln -sf /etc/nginx/sites-available/isgrace /etc/nginx/sites-enabled/isgrace
nginx -t
systemctl reload nginx

echo "=================================================================="
echo "Bootstrap done. Before starting isgrace, edit the real secrets:"
echo "  nano /etc/systemd/system/isgrace.service"
echo "    - SESSION_SECRET      -> output of: openssl rand -hex 32"
echo "    - DEFAULT_LLM_API_KEY -> your real OpenRouter key"
echo "  systemctl daemon-reload"
echo "  systemctl enable --now isgrace"
echo ""
echo "Then add the Cloudflare DNS record (see deploy/README.md), and run"
echo "./deploy/deploy.sh from your local machine to ship the app."
echo "=================================================================="
echo ""
echo "Notes on what this script deliberately does NOT do:"
echo "  - No firewall changes. Node binds to 127.0.0.1 only (server/index.ts),"
echo "    so port 3001 was never reachable externally in the first place —"
echo "    nothing to lock down, and no risk of touching rules bd.limlamleen.com"
echo "    already depends on."
echo "  - No swapfile. This box is already running a live service; if you want"
echo "    a memory safety margin, check 'free -h' and 'swapon --show' yourself"
echo "    and decide — don't want to silently change memory behavior under an"
echo "    already-running production service."
echo "  - 'nginx reload', never 'nginx restart' — reload re-reads config without"
echo "    dropping bd.limlamleen.com's existing connections."
