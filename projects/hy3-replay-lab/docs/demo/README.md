# 演示来源说明

`replaylab-offline-demo.gif` 是对 Hy3 轨迹复盘台真实中文 Web UI 的 12 秒录制。它是离线演示，不是在线 Hy3 录屏。

## 录制流程

1. 选择公开的 `coding-loop` 场景。
2. 通过确定性的离线提供方完成分析。
3. 查看高亮的首个偏航点、验收覆盖、最小重放计划与证据抽屉。
4. 切换到 `research-grounding`，重复偏航与证据查看流程。
5. 普通 Playwright 测试另外验证 JSON 和 Markdown 下载。

五张真实界面帧分别是：

- [场景选择](frames/01-case-picker.png)
- [编程偏航](frames/02-coding-divergence.png)
- [编程证据](frames/03-coding-evidence.png)
- [研究偏航](frames/04-research-divergence.png)
- [研究证据](frames/05-research-evidence.png)

## 复现

在 `frontend/` 中运行：

```powershell
$env:REPLAYLAB_CAPTURE_DEMO = "1"
npx playwright test e2e/demo-capture.spec.ts --project=chromium
```

然后在 `backend/` 中运行：

```console
uv run python ../scripts/build_demo_gif.py
```

截图用例通过与浏览器测试相同的 Playwright 配置启动真实 FastAPI 和 Vite 应用。[`build_demo_gif.py`](../../scripts/build_demo_gif.py) 只用 Pillow 组装截图，不绘制或合成产品界面。

## 隐私与真实性检查

- 页面明确显示“离线演示”。
- 截图只包含公开合成案例数据。
- 不含桌面外框、通知、账号、API Key、个人路径、请求编号或私有轨迹。
- GIF 时长 12 秒，低于两分钟要求。
- 历史 Hy3 两场景结果单独保存在[v1 在线报告](../../evals/results/live-fixtures-2026-07-22.md)中；当前状态见[在线冒烟记录](../../evals/results/live-ui-smoke-2026-07-22.md)。

当前在线分析没有完成，因此本次没有伪造“在线”录屏。完整标注的两场景在线门禁和在线 UI 录制仍待补充。
