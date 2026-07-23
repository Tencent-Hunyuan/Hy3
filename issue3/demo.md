# 演示说明

## 验证客户端

1. 命令行协议客户端 `mcp_client_check.py` — 走完整 stdio 协议
2. MCP Inspector — 官方调试工具

## 建议录屏内容 (≤2 分钟)

1. 展示 `.env.example` / 环境变量 (不露出完整 Key)
2. 运行 `python mcp_client_check.py`，展示 4 个 tools 列表和 `PASS`
3. 运行 `python smoke_test.py`，展示 `load_dataset` 输出和 Hy3 分析结果
4. MCP Inspector 中调用 `load_dataset` / `hy3_analyze` / `hy3_chart_guide`

视频可放在本目录 `demo.mp4`，或使用外链，在 PR 正文注明。
