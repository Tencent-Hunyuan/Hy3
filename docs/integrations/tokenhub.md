# Use Hy3 with TokenHub

## Overview

TokenHub cloud API mode is a setup option for using Hy3 without self-hosting the model.

Verification status: the basic TokenHub Hy3 Chat Completions API smoke test is verified. Five TokenHub client integrations in this PR are verified with screenshots. Remaining unverified items are documented as future verification items.

## TokenHub API Settings

Use these TokenHub settings when configuring an OpenAI-compatible provider:

| Setting | Value |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model ID | `hy3` |
| Provider/protocol | OpenAI-compatible |
| API key | User-created TokenHub API key, never committed |

If the TokenHub API key access scope is limited, Hy3 must be included in that scope.

## Smoke Test

The basic TokenHub Hy3 Chat Completions API path has been manually smoke-tested.

Verified request settings:

| Setting | Value |
|:---|:---|
| Setup mode | Tencent Cloud TokenHub cloud API mode |
| API protocol | OpenAI-compatible Chat Completions API |
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Endpoint | `/chat/completions` |
| Model | `hy3` |
| API key | User-created TokenHub API key, not committed |
| Test prompt | `Hello Hy3. Reply in one short English sentence.` |

Safe PowerShell example:

```powershell
$SecureApiKey = Read-Host "TokenHub API key" -AsSecureString
$ApiKey = [System.Net.NetworkCredential]::new("", $SecureApiKey).Password

try {
    $Body = @{
        model = "hy3"
        messages = @(
            @{
                role = "user"
                content = "Hello Hy3. Reply in one short English sentence."
            }
        )
    } | ConvertTo-Json -Depth 10

    Invoke-RestMethod `
        -Method Post `
        -Uri "https://tokenhub.tencentmaas.com/v1/chat/completions" `
        -Headers @{ Authorization = "Bearer $ApiKey" } `
        -ContentType "application/json" `
        -Body $Body
}
finally {
    Remove-Variable ApiKey -ErrorAction SilentlyContinue
}
```

Observed response summary:

| Field | Observed value |
|:---|:---|
| Response object | `chat.completion` |
| Response model | `hy3` |
| Response content | `Hello! How can I help you today?` |
| Usage fields | Included `prompt_tokens`, `completion_tokens`, `total_tokens`, and `reasoning_tokens` |
| Verification environment | Windows 10 CMD + PowerShell `Invoke-RestMethod` |
| Verification date | 2026-07-08 |

## Account and Availability

- Account signup: Future verification item.
- Billing requirements: Future verification item.
- Regional availability: Future verification item.
- Exact free quota details: Future verification item.
- Hy3 model availability in TokenHub: Future verification item.

Do not add unsupported pricing claims.

## Safety Notes

- Never commit TokenHub API keys.
- Never paste API keys into documentation examples.
- Never add screenshots or GIFs that reveal API keys.
- Use environment variables or the target tool's secret storage when available; exact behavior is documented in verified tool guides where observed.

## Client Configuration

When a tool supports an OpenAI-compatible custom provider, use:

```text
Base URL: https://tokenhub.tencentmaas.com/v1
Model: hy3
API key: <user-created TokenHub API key>
Protocol: OpenAI-compatible
```

Tool-specific UI paths and exact configuration steps are documented in the verified tool guides where observed.
