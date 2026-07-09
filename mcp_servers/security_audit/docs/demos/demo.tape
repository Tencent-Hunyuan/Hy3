# VHS tape — records the MCP stdio client demo to a GIF.
# Reproduce:  env HY3_API_KEY=... HY3_BASE_URL=... HY3_MODEL=... vhs docs/demos/demo.tape
# (run from the hy3-security-mcp/ project root; the API key is read from the
#  environment and never appears in this tape or in the recording.)

Output docs/demos/hy3-security-mcp-demo.gif

Require uv

Set Shell "bash"
Set FontSize 13
Set Width 1180
Set Height 780
Set Padding 14
Set Framerate 12
Set WaitTimeout 120s

Sleep 500ms
Type "uv run python examples/mcp_stdio_client_demo.py"
Sleep 400ms
Enter

# End the recording precisely when the driver prints its final success line.
Wait+Screen /全部经由/
Sleep 2s
