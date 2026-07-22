# 真实 Hy3 在线界面门禁

- 日期：2026-07-22
- Provider：`tencent-tokenhub`
- Model：`hy3-preview`
- 输入：两条公开合成内置案例
- 浏览器：Playwright 1.61.1 / Chrome

## 结果

`REPLAYLAB_CAPTURE_LIVE_DEMO=1 npx playwright test e2e/live-demo-capture.spec.ts --project=chromium` 通过。测试启动真实 FastAPI 与 Vite 服务，在界面中明确选择“在线 Hy3”，依次完成：

1. `coding-loop`：得到 `step-006-repeat-patch`，打开 `ev-repeat-failure` 证据并下载 JSON；
2. `research-grounding`：得到 `step-006-unsupported-causal-leap`，打开 `ev-source-a` 证据并下载 Markdown。

两次在线分析合计 64,719 毫秒，低于 120 秒门禁。两个结果都由界面元数据确认为 `mode=live`。Playwright 用例总耗时约 1.1 分钟。

## 演示产物

- [12 秒在线 GIF](../../docs/demo/replaylab-live-demo.gif)
- [在线场景选择](../../docs/demo/live-frames/01-case-picker.png)
- [编程偏航](../../docs/demo/live-frames/02-coding-divergence.png)
- [编程证据](../../docs/demo/live-frames/03-coding-evidence.png)
- [研究偏航](../../docs/demo/live-frames/04-research-divergence.png)
- [研究证据](../../docs/demo/live-frames/05-research-evidence.png)

截图只包含公开合成数据与本地生成的 ReplayLab 报告编号。视觉复核确认其中没有 API Key、账号、个人路径、TokenHub 请求编号、桌面通知或私有轨迹。

## 配额说明

当前 Key 对 `hy3` 的探针返回 HTTP 402 / 业务码 `401008`，表示该服务的免费体验额度已耗尽且未开启后付费。应用未绕过错误，也未把离线结果改标为在线；本次通过后端既有的 `HY3_MODEL` 配置改用同属 Hy3、支持结构化输出的 `hy3-preview` 完成当前门禁。完整人工标注结果见[在线 fixture 报告](live-fixtures-hy3-preview-2026-07-22.md)。
