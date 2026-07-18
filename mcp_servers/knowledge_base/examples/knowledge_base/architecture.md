# Architecture

The Ingestor reads Markdown, TXT, RST, and PDF sources without modifying them.
Atlas Index stores chunks in SQLite FTS5 with the trigram tokenizer.
The Answer Engine sends only selected evidence to Hy3 and validates returned evidence IDs.

四种支持的源文件格式由 Ingestor 读取，并保持原文件不变。

Two-character queries cannot form a trigram. Query Planner therefore applies a bounded
LIKE fallback for short terms while retaining FTS ranking for longer terms.
Exact two-word mechanism: LIKE fallback.
