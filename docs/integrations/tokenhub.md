# Use Hy3 with TokenHub

## Overview

TokenHub cloud API mode is a setup option for using Hy3 without self-hosting the model.

Verification status: TODO: verify manually.

## TokenHub API Settings

Use these TokenHub settings when configuring an OpenAI-compatible provider:

| Setting | Value |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model ID | `hy3` |
| Provider/protocol | OpenAI-compatible |
| API key | User-created TokenHub API key, never committed |

If the TokenHub API key access scope is limited, Hy3 must be included in that scope.

## Account and Availability

- Account signup: TODO: verify manually.
- Billing requirements: TODO: verify manually.
- Regional availability: TODO: verify manually.
- Hy3 model availability in TokenHub: TODO: verify manually.

Do not add unsupported pricing claims.

## Safety Notes

- Never commit TokenHub API keys.
- Never paste API keys into documentation examples.
- Never add screenshots or GIFs that reveal API keys.
- Use environment variables or the target tool's secret storage when available: TODO: verify manually per tool.

## Client Configuration

When a tool supports an OpenAI-compatible custom provider, use:

```text
Base URL: https://tokenhub.tencentmaas.com/v1
Model: hy3
API key: <user-created TokenHub API key>
Protocol: OpenAI-compatible
```

Tool-specific UI paths and exact configuration steps: TODO: verify manually.
