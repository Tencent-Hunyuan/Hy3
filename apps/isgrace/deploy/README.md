# Deploying isGrace to isgrace.limlamleen.com

Target: `43.156.131.187` — a server that **already runs `bd.limlamleen.com`** via nginx (the `athenax-dashboard` FastAPI app, on port 8080). Everything here is additive: a new nginx site, a new systemd service, a new Cloudflare DNS record. Nothing here touches `sites-available/athenax-dashboard`, the `athenax-dashboard` systemd service, or restarts nginx (only ever `reload`).

## 0. DNS (one-time, do this first)

`bd.limlamleen.com` is Cloudflare-proxied (orange cloud) with TLS terminated at Cloudflare's edge, not locally — nginx on the box only ever speaks plain HTTP. Add the same setup for `isgrace`:

At Cloudflare's dashboard for `limlamleen.com`, add:

```
Type: A
Name: isgrace
Content: 43.156.131.187
Proxy status: Proxied (orange cloud)
```

No certbot, no local TLS config needed — Cloudflare handles HTTPS the same way it already does for `bd`.

## 1. Precondition: complete onboarding locally first

Before deploying, run the app locally (`npm run dev`), go through onboarding, upload the demo course materials, and get the teaching flow into the state you want visitors to see. The deploy only ships code — your local `data/` directory (materials, config, cheatsheets) is synced up **once, manually**, in step 4. If `data/config.json`'s `onboardingComplete` is ever `false` on the server, visitors would hit the onboarding wizard instead of the app.

## 2. First-time server bootstrap

From your local machine:

```bash
scp deploy/bootstrap.sh deploy/isgrace.service deploy/nginx-isgrace.conf root@43.156.131.187:/root/
ssh root@43.156.131.187
bash bootstrap.sh
```

This installs Node (skipped if already present — it likely is, for the dashboard app), creates a dedicated unprivileged `isgrace` system user (separate from whatever runs the dashboard), installs the systemd unit, and adds `/etc/nginx/sites-available/isgrace` + symlinks it into `sites-enabled/` — a **new file**, `sites-available/athenax-dashboard` is never opened or edited. Ends with `nginx -t && systemctl reload nginx` (reload, never restart, so `bd.limlamleen.com` never drops a connection).

Deliberately **not** done by this script, and why:
- **No firewall changes.** `server/index.ts` binds the Node process to `127.0.0.1` only, so port 3001 was never reachable from outside the box regardless of firewall rules — nothing to lock down, and no risk of touching whatever rules `bd.limlamleen.com` already relies on.
- **No swapfile.** This is a live box already running another service — if you want a memory safety margin, check `free -h` yourself and decide; don't want to silently change memory behavior under something already in production.

## 3. Fill in the real secrets (on the server — never commit these to the repo)

```bash
openssl rand -hex 32   # copy this for SESSION_SECRET

nano /etc/systemd/system/isgrace.service
#   SESSION_SECRET=<paste the random hex above>
#   DEFAULT_LLM_API_KEY=<your real OpenRouter key>

systemctl daemon-reload
systemctl enable --now isgrace
```

## 4. One-time: seed your local demo course data

**Run this by hand, once. Do not add it to `deploy.sh`** — repeating it would overwrite anything visitors have done since (though since the workspace is shared, not per-user, that's usually fine — just don't make it an automatic habit that surprises you).

```bash
rsync -avz data/ root@43.156.131.187:/opt/isgrace/data/
```

## 5. Deploy (every time you change code)

From your local machine, repo root:

```bash
./deploy/deploy.sh
```

Builds the frontend locally, then ships `dist/`, `server/`, `src/types/`, and `package.json`/`package-lock.json`. Only ever restarts the `isgrace` service — never touches nginx or the dashboard service. `data/` is never touched by this script.

## 6. Verify

```bash
ssh root@43.156.131.187 "systemctl status isgrace"
ssh root@43.156.131.187 "systemctl status athenax-dashboard"  # confirm bd is still fine, unaffected
ssh root@43.156.131.187 "journalctl -u isgrace -f"             # tail logs
curl -I https://isgrace.limlamleen.com/api/auth/me             # should be 200
curl -I https://bd.limlamleen.com/                             # confirm bd is still reachable
```

Then open `https://isgrace.limlamleen.com` in a browser — you should see the email gate, and after entering any email, the app using the shared default Hy3 key with no key configured on your end.

## Notes

- `SESSION_SECRET` being set is what turns on the whole hosted-mode behavior (login gate + key redaction) — if you ever need to temporarily disable the login wall, unset it and restart, but note that also stops redacting the default key from `GET /api/settings`, so don't do that on a publicly reachable box.
- Visitor emails are logged to `/opt/isgrace/data/visitors.jsonl` (one JSON object per line) — no verification, just whatever a visitor typed.
- If a visitor supplies their own API key via Settings, it's stored in *their own browser's* localStorage and only ever sent per-request as an override — it never touches this server's `data/settings.json` or gets logged anywhere.
- SSE streaming (the chat responses) needs `proxy_buffering off` in nginx — already set in `nginx-isgrace.conf` — otherwise nginx buffers the whole response before forwarding it and the UI never sees incremental tokens.
