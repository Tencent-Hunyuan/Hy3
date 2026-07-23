# 第二个 MCP 客户端：官方 MCP Inspector

用法：在 issue3 目录执行：

```bash
npx @modelcontextprotocol/inspector python server.py
```

浏览器打开后：
1. 确认 Command 指向 python，Args 为 server.py
2. Connect
3. Tools 列表应出现 load_dataset / web_search / hy3_analyze / hy3_chart_guide
4. 调用 load_dataset，path 填 sample_data.csv
5. 调用 web_search，query 填 test
6. 调用 hy3_analyze，dataset_path 填 sample_data.csv，question 填「简要分析数据趋势」
