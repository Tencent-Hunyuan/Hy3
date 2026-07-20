# 临时存储目录

此目录用于代码评审过程中暂存 `get_file_content` 的输出。
每个 `round_N_<uuid>.md` 文件对应一轮评审中混元请求的所有文件。
调用 `reset_review` 时自动清空所有轮次文件。
本 README.md 不会被删除。
