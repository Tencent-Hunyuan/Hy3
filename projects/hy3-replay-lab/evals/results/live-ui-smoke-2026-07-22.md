# Historical live UI smoke check

- Date: 2026-07-22
- Surface: running Simplified-Chinese Web UI
- Fixture: `coding-loop`
- Provider/model: `tencent-tokenhub` / `hy3`

Two explicit analysis attempts ended with the product's bounded `Hy3 分析请求失败` error and produced no report. A read-only `GET /v1/models` probe against the configured endpoint returned HTTP 200 between the attempts, so endpoint access was available while analysis completion was not reproducible.

No request ID, response body, credential, account data, raw prompt, or private trace is stored. This smoke check is availability evidence only; it is not a model-quality measurement. A later status-only probe resolved this `hy3` failure as HTTP 402 / business code `401008`. It is superseded for release gating by the current [2/2 Hy3 Preview fixture result](live-fixtures-hy3-preview-2026-07-22.md) and [live browser record](live-ui-demo-2026-07-22.md), while remaining here as failure-path history.
