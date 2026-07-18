# Hy3 Knowledge Base MCP Evaluation

- Model: tencent/hy3:free
- Endpoint profile: openrouter
- Reasoning effort: none
- Package version: 0.1.0
- Git commit: bff5522
- Corpus SHA-256: 7900b86f2d1f7c7bb979e9ecbc1ae09f2e4d83f461ad25188c1cd423882da7d5
- Transport: stdio
- Corpus: examples/knowledge_base
- Questions: 10
- Endpoint host: openrouter.ai
- UTC timestamp: 2026-07-11T09:27:39Z
- Retrieval: search limit 12; ask top-k 12
- Score: 10/10 (100.0%)

| # | Result | Duration (s) | Question | Expected | Actual | Sources | Search hits | Citations | Failure |
|---:|:---:|---:|---|---|---|---|---|---|---|
| 1 | PASS | 2.641 | The milestone that requires verification in two named clients is also the production launch. What is its date? Respond with only YYYY-MM-DD. | 2025-11-18 | 2025-11-18 | roadmap.md | charter.md, roadmap.md, runbook.txt, architecture.md, incident-review.md | charter.md, roadmap.md |  |
| 2 | PASS | 1.937 | Which component sends selected evidence to the remote model after local retrieval? Respond with only the component name. | Answer Engine | Answer Engine | architecture.md | architecture.md, security-policy.rst, roadmap.md, runbook.txt, charter.md | architecture.md |  |
| 3 | PASS | 1.875 | 中文“退款”短查询事故持续了多少分钟？仅回复整数。 | 27 | 27 | incident-review.md | incident-review.md, roadmap.md | incident-review.md |  |
| 4 | PASS | 1.735 | What exact fallback addresses the trigram limitation for short terms? Respond with only the two-word mechanism. | LIKE fallback | LIKE fallback | architecture.md | architecture.md, incident-review.md, runbook.txt | architecture.md |  |
| 5 | PASS | 1.922 | Which document classification is prohibited from entering the index at all? Respond with only the classification. | Restricted | Restricted | security-policy.rst | security-policy.rst, runbook.txt, architecture.md, incident-review.md | security-policy.rst |  |
| 6 | PASS | 1.703 | When remote generation is rate-limited, which MCP tool remains available for local evidence lookup? Respond with only the tool name. | hy3_kb_search | hy3_kb_search | runbook.txt | charter.md, runbook.txt, security-policy.rst, architecture.md | runbook.txt |  |
| 7 | PASS | 1.859 | On what date did page-cited PDF ingestion become a roadmap deliverable? Respond with only YYYY-MM-DD. | 2025-09-15 | 2025-09-15 | roadmap.md | roadmap.md, architecture.md, charter.md | roadmap.md |  |
| 8 | PASS | 1.719 | 哪个架构组件读取四种支持的源文件格式并保持原文件不变？仅回复组件名。 | Ingestor | Ingestor | architecture.md | architecture.md | architecture.md |  |
| 9 | PASS | 1.797 | Who sponsors the project whose final milestone requires Cline and TRAE verification? Respond with only the person's name. | Mei Lin | Mei Lin | charter.md, roadmap.md | roadmap.md, charter.md, security-policy.rst | roadmap.md, charter.md |  |
| 10 | PASS | 1.719 | If the required SQLite tokenizer is unavailable, what must the server do instead of performing an unbounded scan? Respond with only the two-word action. | Stop indexing | Stop indexing | runbook.txt | runbook.txt, security-policy.rst, architecture.md, charter.md | runbook.txt |  |
