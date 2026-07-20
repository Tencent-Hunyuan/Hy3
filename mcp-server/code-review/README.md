# Code Review MCP Server (Hy3)

基于混元大模型 (Hy3) 的代码评审 MCP Server ，通过 SSE 协议（方便后续公网部署）与 MCP 客户端通信。



## 快速开始

### mcp server 启动

```bash
git clone https://github.com/luohuixi/Hy3/tree/main
cd mcp-server/code-review
pip install -r requirements.txt
cp .env.example .env          			  # 编辑 .env 填入 API Key
python server.py --port 8000              # 启动 MCP Server (SSE 模式)
```



### .env 示例

```yaml
hy3_api_key=your-hy3-api-key
hy3_base_url=https://tokenhub.tencentmaas.com/v1
```



### MCP 客户端注册

```json
{
  "mcpServers": {
    "code-review-hy3": {
      "type": "sse",
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```



## Tool 列表

### `get_review_guide`

返回代码评审的详细行为规范、提示词模板和工作流程。避免过长的描述放置在 mcp 的 instruction 中占用系统上下文。



### `get_diff_stats`

查看 git diff 变更文件清单和项目目录树。变更文件在目录树中标注 `[ADDED]`/`[MODIFIED]`/`[DELETED]`/`[RENAMED]`。

| 参数 | 必需 | 说明 |
|------|------|------|
| `project_root` | ✓ | 项目根目录绝对路径 |
| `base_branch` | — | 对比基准分支（默认 main） |



### `get_file_content`

读取文件内容并加上标注 `[ADDED]`/`[MODIFIED]`/`[DELETED]`/`[RENAMED]`，暂存到服务端 tmp 目录。返回简短摘要，无需客户端 Agent 读取全部内容，可节约 token 消耗。

| 参数 | 必需 | 说明 |
|------|------|------|
| `project_root` | ✓ | 项目根目录 |
| `file_path` | ✓ | 相对于 project_root 的文件路径 |
| `base_branch` | — | 对比基准（默认 main） |



### `review_with_hunyuan`

将内容发给混元，返回自然语言响应。服务端自动维护对话记忆。

| 参数 | 必需 | 说明 |
|------|------|------|
| `content` | — | 直接发送的消息文本 |
| `use_tmp` | — | True 则读取 tmp 暂存文件发给混元 |



### `reset_review`

清空混元对话记忆和临时文件，开始新一轮评审。



## 评审工作流

核心思路：

mcp 客户端只负责调用工具传输信息，不负责审核，审核应交由 mcp server 端连接的**混元大模型**负责，客户端将项目树，变更文件等内容发送给混元，混元决定审核顺序，并根据项目树请求具体文件的内容，审核完毕后返回给客户端，客户端将结果返回给用户。

期望 mcp 客户端 agent 的行为流程：

1. `get_diff_stats` → 获取项目树 + 变更文件
2. `review_with_hunyuan` → 发给混元（首次）
3. 混元自然语言根据项目树回复需要查看哪些文件
4. `get_file_content` → 读取混元要求的文件（带 diff 标注）
5. `review_with_hunyuan(use_tmp=True)` → 将暂存内容发给混元
6. 重复 3-5 直到混元给出最终评审
7. `reset_review` → 清空记忆
