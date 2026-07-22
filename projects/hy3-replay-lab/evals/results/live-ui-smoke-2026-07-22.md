# Live UI smoke check

- Date: 2026-07-22
- Surface: running Simplified-Chinese Web UI
- Fixture: `coding-loop`
- Provider/model: `tencent-tokenhub` / `hy3`

Two explicit analysis attempts ended with the product's bounded `Hy3 分析请求失败` error and produced no report. A read-only `GET /v1/models` probe against the configured endpoint returned HTTP 200 between the attempts, so endpoint access was available while analysis completion was not reproducible.

No request ID, response body, credential, account data, raw prompt, or private trace is stored. This smoke check is availability evidence only; it is not a model-quality measurement. The current full-annotation two-fixture live gate remains outstanding.
