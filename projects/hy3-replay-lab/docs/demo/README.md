# 演示来源说明

`replaylab-live-demo.gif` 是 Hy3 轨迹复盘台真实中文 Web UI 的 12 秒在线演示。Playwright 启动实际 FastAPI 与 Vite 服务，界面明确选择“在线 Hy3”，两条公开案例均由 TokenHub `hy3-preview` 返回并通过本地确定性校验。

`replaylab-offline-demo.gif` 保留为无需 Key 即可复现的离线演示，页面始终显示“离线演示”，不会与在线证据混用。

## 在线录制流程

1. 选择“在线 Hy3”，运行 `coding-loop`。
2. 定位 `step-006-repeat-patch`，查看 `ev-repeat-failure`，下载 JSON。
3. 运行 `research-grounding`。
4. 定位 `step-006-unsupported-causal-leap`，查看 `ev-source-a`，下载 Markdown。

两次在线分析合计 64,719 毫秒，低于两分钟门禁。五张在线界面帧是：

- [场景选择](live-frames/01-case-picker.png)
- [编程偏航](live-frames/02-coding-divergence.png)
- [编程证据](live-frames/03-coding-evidence.png)
- [研究偏航](live-frames/04-research-divergence.png)
- [研究证据](live-frames/05-research-evidence.png)

对应的离线帧保存在 [`frames/`](frames/)。

## 复现

在线录制要求后端进程环境已经配置 `HY3_API_KEY`、`HY3_BASE_URL` 和可用的 `HY3_MODEL`。在 `frontend/` 中运行：

```powershell
$env:REPLAYLAB_CAPTURE_LIVE_DEMO = "1"
npx playwright test e2e/live-demo-capture.spec.ts --project=chromium
```

离线录制不消耗 Hosted 配额：

```powershell
$env:REPLAYLAB_CAPTURE_DEMO = "1"
npx playwright test e2e/demo-capture.spec.ts --project=chromium
```

然后在 `backend/` 中组装对应 GIF：

```console
uv run python ../scripts/build_demo_gif.py --mode live
uv run python ../scripts/build_demo_gif.py --mode offline
```

截图用例通过与普通浏览器测试相同的 Playwright 配置驱动真实应用。[`build_demo_gif.py`](../../scripts/build_demo_gif.py) 只用 Pillow 缩放并串联截图，不绘制或伪造产品界面。

## 隐私与真实性检查

- 在线帧的模式按钮和结果元数据都显示“在线 Hy3”；离线帧保留原标签。
- 截图只包含公开合成案例和本地生成的 ReplayLab 报告编号。
- 视觉复核确认没有桌面外框、通知、账号、API Key、个人路径、TokenHub 请求编号或私有轨迹。
- 两个 GIF 均为 12 秒；在线调用实际耗时 64,719 毫秒，均低于两分钟要求。
- 当前 2/2 完整标注结果见[在线 fixture 报告](../../evals/results/live-fixtures-hy3-preview-2026-07-22.md)，浏览器执行记录见[在线界面门禁](../../evals/results/live-ui-demo-2026-07-22.md)。
