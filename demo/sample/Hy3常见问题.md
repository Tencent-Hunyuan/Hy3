# Hy3 常见问题（FAQ）

**Q1：Hy3 支持多长的上下文？**
A：原生支持 256k 上下文，适合长文档与代码库场景。

**Q2：如何调用 Hy3？**
A：通过 OpenAI 兼容接口 `https://tokenhub.tencentmaas.com/v1`，在请求头带 Bearer Token，模型名设为 `hy3`。

**Q3：推理模式有什么用？**
A：`reasoning_effort` 可设为 `no_think`、`low`、`high`。`low` 适合快速问答，`high` 适合复杂推理。

**Q4：Hy3 适合做 RAG 吗？**
A：非常适合。它能在检索到的片段基础上生成带引用的回答，是端到端检索增强问答的理想底层模型。

**Q5：需要本地部署吗？**
A：不需要。全程通过 API 调用即可，不依赖本地算力或微调。
