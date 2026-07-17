# 运行时记忆目录（runtime memory）

本目录保存应用运行期间的持久化状态，**不纳入 git**（见根目录 `.gitignore`）。

- `documents.json` — 已导入文档的元数据（文件名、分块数、所属文件夹等），用于文档记忆持久化。
- `folders.json` — 文件夹归类信息。
- `conversations/` — 每个会话的消息历史 JSON（按 `conversation_id` 存储）。

> 删除这些文件只会清空「记忆」，不会删除已上传的原始文档（原始文件在 `../uploads/`）。
> 重新导入文档即可重建。
