# 第二个 MCP 客户端：官方 MCP Inspector
# 用法：双击 start_inspector.cmd，或在本目录执行：
#   npx --yes @modelcontextprotocol/inspector D:\Anaconda\python.exe D:\work\hy3-mcp-server\server.py
#
# 浏览器打开后：
# 1. 确认 Command/Args 指向上面的 python 与 server.py
# 2. Connect
# 3. Tools 列表应出现 list_dir / read_file / hy3_code_review / hy3_answer
# 4. 调用 list_dir，path 填 .
# 5. 可选：调用 hy3_answer，question 填「只回复ok」
