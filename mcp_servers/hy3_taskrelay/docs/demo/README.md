# Cross-client demo evidence

The 13.2-second [`taskrelay_cross_client.gif`](taskrelay_cross_client.gif) shows the verified
cross-client flow over one public synthetic fixture:

1. CodeBuddy Code 2.124.0 calls `taskrelay_create_checkpoint` and creates
   `cp_b3067b1cc7f4a430`.
2. The exact portable checkpoint crosses the client boundary.
3. Codex CLI 0.144.6 calls `taskrelay_audit_checkpoint` (`clean`, zero findings) and
   `taskrelay_create_resume_brief` (`resume_bff690737dece30f`, priorities 1 → 2).

[`codebuddy_actual_call.png`](codebuddy_actual_call.png) and
[`codex_actual_calls.png`](codex_actual_calls.png) are sanitized terminal-style captures rendered
from the verified real-client event records. They preserve the client versions, modes, exact tool
names, successful exits, artifact IDs, statuses, and counts. They are not raw desktop pixels:
credentials, prompts, provider responses, request metadata, account data, and local paths are
deliberately omitted before rendering.

[`codebuddy_checkpoint.png`](codebuddy_checkpoint.png) and
[`codex_audit_resume.png`](codex_audit_resume.png) are supplementary artifact-summary cards. All
images and the GIF are generated from [the committed sanitized client records](../clients) and
[schema-valid artifacts](../client_artifacts), not from invented demo results.

Regenerate the evidence after installing development dependencies:

```bash
python scripts/render_client_demo.py
```
