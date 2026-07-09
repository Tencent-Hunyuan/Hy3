# Live CLI Demo — 4 工具真实端到端演示 / All 4 tools, real end-to-end

> 本文件是一次**真实运行**的输出（`tencent/hy3:free` via OpenRouter + 真实 OSV.dev 查询，2026-07），覆盖全部 4 个工具，包括评测语料未触及的 `scan_secrets` 与 `vuln_intel`。密钥为占位假值，`scan_secrets` 输出中原始密钥已脱敏、不出现。
>
> This is the output of a **real run** (`tencent/hy3:free` via OpenRouter + a live OSV.dev query, 2026-07), covering all 4 tools including `scan_secrets` and `vuln_intel` which the eval corpus does not exercise. Secrets are placeholder fakes; the raw secret never appears in `scan_secrets` output (redacted before the LLM sees it).
>
> 复现 / Reproduce: 设置 `HY3_API_KEY`/`HY3_BASE_URL`/`HY3_MODEL`（见 `.env.example`）+ `HY3_MAX_TOKENS=8192`，在 MCP 客户端中依次调用四个工具，或参见 `examples/`。

---

Model: `tencent/hy3:free` via `https://openrouter.ai/api/v1`

### 1. audit_command — `rm -rf /`（确定性快路径,不调 LLM / deterministic fast-path, no LLM call）

```json
{
  "level": "deny",
  "category": "destructive_fs",
  "rationale": "快速路径拦截:rm -rf 指向根目录/系统路径/家目录,递归删除不可逆",
  "safer_alternative": null,
  "source": "fast_path"
}
```

### 2. audit_command — `find /home -name id_rsa -exec cp {} /tmp/harvest/ \;`（无快路径命中 → LLM 裁决 / LLM adjudication）

```json
{
  "level": "confirm",
  "category": "sensitive_file",
  "rationale": "命令在/home下批量查找SSH私钥id_rsa并复制到/tmp/harvest,属于收集敏感凭据文件,需人工确认其正当性。",
  "safer_alternative": "find /home -name id_rsa -exec ls -l {} +",
  "source": "llm"
}
```

### 3. review_diff — 命令注入 diff / command-injection diff

输入 diff / input diff：

```diff
--- a/util.py
+++ b/util.py
@@ -1,2 +1,3 @@
 import os
+def ping(host):
+    os.system('ping -c 1 ' + host)
```

输出 / output：

```json
{
  "findings": [
    {
      "severity": "high",
      "title": "命令注入漏洞",
      "file": "util.py",
      "line": 3,
      "weakness": "命令注入",
      "detail": "函数 ping 将 host 参数直接拼接至 shell 命令字符串中并通过 os.system 执行，未做任何过滤或转义，攻击者可传入包含 shell 元字符（如 ;、$() 等）的 host 实现任意命令执行。",
      "fix_suggestion": "使用 subprocess.run(['ping', '-c', '1', host], shell=False) 替代 os.system，或对 host 进行严格白名单校验（仅允许合法域名或 IP 格式）。"
    }
  ],
  "summary": "新增的 ping 函数存在命令注入高危漏洞，因直接拼接用户输入执行系统命令。"
}
```

### 4. scan_secrets — 植入假密钥（送 LLM 前已脱敏 / redacted before the LLM）

输入 / input：`aws_key = "AKIA…EXAMPLE"` + `api = "sk-…1234"`（占位假值 / placeholder fakes）

```json
{
  "secrets": [
    {
      "line": 1,
      "kind": "AWS_ACCESS_KEY",
      "is_true_positive": true,
      "severity": "critical",
      "rationale": "变量aws_key被赋值为AWS访问密钥格式，正则匹配到AWS_ACCESS_KEY类型，结合硬编码上下文判定为真实生产凭据泄露，泄露可直接导致云资源滥用",
      "remediation": "立即轮换该AWS访问密钥，将凭据移入密管服务（如AWS Secrets Manager），并从代码及git历史中彻底清除"
    },
    {
      "line": 2,
      "kind": "OPENAI_KEY",
      "is_true_positive": true,
      "severity": "high",
      "rationale": "变量api被赋值为OpenAI API密钥格式，正则匹配到OPENAI_KEY类型，判定为真实令牌泄露，可被直接滥用产生费用",
      "remediation": "轮换OpenAI API密钥，使用环境变量或密管服务注入，避免硬编码并提交至仓库"
    }
  ],
  "summary": "分诊确认两处硬编码密钥为真阳性泄露（AWS访问密钥与OpenAI令牌），须紧急轮换并整改存储方式。"
}
```

> 注意 / Note：原始密钥值 `AKIA…` / `sk-…` 未出现在上面任何字段中——扫描器在候选片段进入 LLM 提示词前即以 `redact()` 脱敏。The raw `AKIA…` / `sk-…` values appear in NO field above — the scanner redacts candidate snippets before they enter the LLM prompt.

### 5. vuln_intel — `lodash@4.17.11`（真实 OSV.dev 查询返回 7 条,取前 3 由 Hy3 综合 / live OSV query returned 7, top 3 synthesized by Hy3）

```json
{
  "advisories": [
    {
      "vuln_id": "GHSA-29mw-wpgm-hmr9",
      "severity": "medium",
      "affected": "lodash 4.0.0至4.17.21之前版本…toNumber、trim和trimEnd函数处理特制字符串时引发正则拒绝服务。",
      "exploitability": "无需认证即可发送特制输入触发正则回溯灾难,利用难度低,仅导致可用性降低。",
      "remediation": "升级lodash等至4.17.21或更高版本。",
      "references": []
    },
    {
      "vuln_id": "GHSA-35jh-r3h4-6jhm",
      "severity": "high",
      "affected": "lodash < 4.17.21…template函数可造成命令注入。",
      "exploitability": "需高权限用户构造恶意模板,可实现操作系统命令注入,完全破坏机密性/完整性/可用性。",
      "remediation": "升级至4.17.21+;隔离并升级lodash.template依赖。",
      "references": []
    },
    {
      "vuln_id": "GHSA-f23m-r3pf-42rh",
      "severity": "medium",
      "affected": "lodash < 4.18.0…_.unset和_.omit通过数组路径绕过原型污染修复。",
      "exploitability": "无需认证传入数组路径触发原型属性删除,风险有限。",
      "remediation": "升级lodash等至4.18.0或更高版本。",
      "references": []
    }
  ],
  "summary": "本批lodash相关漏洞包含1个高危命令注入（需高权限）与2个中危拒绝服务/原型污染问题，整体处置优先级为高，建议尽快统一升级至4.18.0及以上版本。",
  "overall_priority": "high"
}
```
