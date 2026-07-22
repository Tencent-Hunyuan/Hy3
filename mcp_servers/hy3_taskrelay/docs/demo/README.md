# 跨客户端演示证据

13.2 秒的 [`taskrelay_cross_client.gif`](taskrelay_cross_client.gif) 使用中文信息图展示同一份
公开合成 fixture 上经过验证的跨客户端流程：

1. CodeBuddy Code 2.124.0 调用 `taskrelay_create_checkpoint`，生成
   `cp_b3067b1cc7f4a430`。
2. 完整的可携带 checkpoint 跨越客户端边界。
3. Codex CLI 0.144.6 调用 `taskrelay_audit_checkpoint`（`clean`、0 个发现项），再调用
   `taskrelay_create_resume_brief`（`resume_bff690737dece30f`、优先级 1 → 2）。

[`codebuddy_actual_call.png`](codebuddy_actual_call.png) 和
[`codex_actual_calls.png`](codex_actual_calls.png) 是从经过验证的真实客户端事件记录生成的
中文展示面板。它们保留客户端版本、运行模式、精确工具名、成功退出、artifact ID、状态和
计数。它们不是原始桌面像素；凭据、Prompt、Provider 响应、请求元数据、账户数据和个人
路径在渲染前已主动排除。

[`codebuddy_checkpoint.png`](codebuddy_checkpoint.png) 和
[`codex_audit_resume.png`](codex_audit_resume.png) 是补充产物摘要卡。四张 PNG 和 GIF
全部由 Pillow 确定性绘制，所有数据均来自[已提交的脱敏客户端记录](../clients)和
[通过 Schema 校验的产物](../client_artifacts)，没有添加示例结果。

安装开发依赖后可重新生成：

```bash
python scripts/render_client_demo.py
```
