# Live Hy3 demo run

[Back to Hy3 Repo Scout](../../README.md) | [中文说明](../../README_CN.md) |
[Terminal GIF](../media/hy3-repo-scout-live-demos.gif)

Both built-in acceptance flows were executed through the OpenRouter Chat Completions API. The
reports below are the output of the recorded run, not fixture text or copied preflight results.

## Runtime

| Field | Value |
|---|---|
| Captured (UTC) | `2026-07-13T03:08:59+00:00` |
| Captured (Asia/Shanghai) | `2026-07-13T11:08:59+08:00` |
| Provider | OpenRouter (`https://openrouter.ai/api/v1`) |
| Model | `tencent/hy3:free` |
| CLI | `hy3-repo-scout 0.1.0` |
| Reasoning effort | `high` |
| Model rounds | `9` maximum; final two available for synthesis and citation repair |
| Tool calls | `32` maximum |
| Repository context | `120000` characters maximum |
| Tool result | `24000` characters maximum |
| Completion | `16384` tokens maximum per request |
| Request timeout | `90` seconds |

The API credential was loaded from the ignored local `.env`. Asciinema captured output only,
with input capture disabled and only `SHELL` included in cast metadata. A byte-for-byte credential
scan of the reports, cast, plain transcript, and GIF passed before delivery.

## Outcomes

| Demo | Exit | Rounds | Tool calls | Files read | Context chars | Total tokens | Citations |
|---|---:|---:|---:|---:|---:|---:|---:|
| [Reasoning-mode change impact](change-impact.md) | 0 | 8 | 23 | 16 | 58852 | 132379 | 58 verified |
| [LoRA pipeline audit](lora-pipeline-audit.md) | 0 | 6 | 21 | 16 | 89436 | 170574 | 51 verified |

Both reports have finish reason `stop`, did not exhaust a local budget, and passed evidence-backed
citation validation without using the reserved repair round.

## Recording

The uncompressed live terminal session took `448.74` seconds. API wait periods were capped during
rendering; the committed GIF is `37.98` seconds, 25 frames, and `1007308` bytes, below the two-minute
activity limit.

```bash
./demos/run-live-demos.sh
```

| Artifact | SHA-256 |
|---|---|
| `change-impact.md` | `c3b0c48253aa9e80bf0e4fee17c5aad3c31859a255739a1e07bbf71b3b9cc495` |
| `lora-pipeline-audit.md` | `d3feb14bc5e33d7c5cb587180e1bf9d1793c0a1ccdcd28ddb26992fbdc6158e9` |
| `hy3-repo-scout-live-demos.gif` | `6d9477e1f12303c6791feb1da78bd247f25031daecc1129bb885c962b568ce49` |
