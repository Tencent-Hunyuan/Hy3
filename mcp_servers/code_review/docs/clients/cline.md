# Cline (VS Code extension)

Verified with Cline on VS Code (Windows 10).

## 1. Install

VS Code → Extensions (`Ctrl+Shift+X`) → search **Cline** (author: saoudrizwan) → Install.

## 2. Configure the MCP server

Open the Cline sidebar → **MCP Servers** → **Configure MCP Servers**. This opens
`cline_mcp_settings.json`. Merge in the config from
[`examples/clients/cline.json`](../../examples/clients/cline.json):

```json
{
  "mcpServers": {
    "hy3-code-review": {
      "command": "uvx",
      "args": ["hy3-code-review-mcp"],
      "env": {
        "HY3_BASE_URL": "https://openrouter.ai/api/v1",
        "HY3_API_KEY": "<your-openrouter-api-key>",
        "HY3_MODEL": "tencent/hy3:free"
      }
    }
  }
}
```

Save. The server row should turn **green** and list three tools:
`review_diff`, `analyze_file`, `git_diff_review`.

### Windows note — `spawn uvx ENOENT`

If Cline reports `spawn uvx ENOENT`, it means `uvx` is not on the PATH that
VS Code inherits (common when `uv` lives inside a conda env). Use the absolute
path to `uvx.exe` instead, e.g.:

```json
"command": "C:\\path\\to\\uvx.exe",
```

Find it with `where uvx` (cmd) or `(Get-Command uvx).Source` (PowerShell).

## 3. Verify

In the Cline chat, paste:

```
用 hy3-code-review 的 review_diff 工具审查这段 diff，reasoning_effort 用 low：

diff --git a/auth/login.py b/auth/login.py
--- a/auth/login.py
+++ b/auth/login.py
@@ -9,7 +9,8 @@ def login(username, password):
-    user = db.query("SELECT * FROM users WHERE name='" + username + "'")
-    if user.password == password:
+    import hashlib
+    user = db.query("SELECT * FROM users WHERE name='" + username + "'")
+    if user.password == hashlib.md5(password.encode()).hexdigest():
         return make_session(user)
     return None
```

Approve the tool call. Hy3 returns a severity-tagged review flagging the SQL
injection (CRITICAL) and the weak MD5 hash (HIGH), with verdict REQUEST CHANGES.
