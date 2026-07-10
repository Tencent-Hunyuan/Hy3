# Use Hy3 with TokenHub

## Overview

TokenHub cloud API mode is a setup option for using Hy3 without self-hosting the model.

Verification status: the basic TokenHub Hy3 Chat Completions API smoke test is verified. All TokenHub client integrations listed in the integrations README are verified with screenshots. Remaining unverified items are documented as future verification items.

## TokenHub API Settings

Use these TokenHub settings when configuring an OpenAI-compatible provider:

| Setting | Value |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model ID | `hy3` |
| Provider/protocol | OpenAI-compatible |
| API key | User-created TokenHub API key, never committed |

Create the API key in the selected TokenHub region. If a limited access scope is used, `hy3` must be included. See [API Key creation and access scope](https://cloud.tencent.com/document/product/1823/130090).

### Region Selection

TokenHub uses region-specific domains. Select the endpoint that matches the region where your TokenHub service and API key were created.

| TokenHub service region | Default base URL | Resource scope | Verification in this PR |
|:---|:---|:---|:---|
| Guangzhou | `https://tokenhub.tencentmaas.com/v1` | China mainland | Verified |
| Singapore | `https://tokenhub-intl.tencentmaas.com/v1` | Global | Not verified |

The endpoint must match the TokenHub service and API-key region. Cross-region and cross-site service calls are not supported. All screenshots and tool-specific runs in this PR used the Guangzhou / China-mainland endpoint.

The Singapore / global endpoint is documented from the official [API domains and regional routing](https://cloud.tencent.com/document/product/1823/130078) reference but was not tested in this PR.

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
| Verification environment | Windows 11 25H2 (build 26200) |
| Verification date | 2026-07-08 |

## Account and Availability

- Account signup: Future verification item.
- Billing requirements: Future verification item.
- Regional availability: Guangzhou / China-mainland was verified. Singapore / global is documented from official TokenHub documentation but was not tested in this PR.
- Exact free quota details: Future verification item.
- TokenHub account-level model access scope for Hy3: Future verification item.

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
