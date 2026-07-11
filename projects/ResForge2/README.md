# Hy3 Research Assistant

基于腾讯混元 Hy3 的个人深度研究助手 — 论文摄入、多源搜索、知识图谱、自动总结与引用生成。

Resolves: issue#4

## 仓库地址
https://github.com/wangyue377/ResForge2

## 项目简介
面向科研场景的个人深度研究助手，围绕论文阅读、文献调研、知识管理场景设计。用户可输入论文 PDF、ArXiv ID 或搜索关键词，系统自动完成论文摄入、语义分块、向量化索引、知识图谱构建、多源文献搜索、论文总结和引用生成等完整科研工作流。

## Hy3 在系统中承担的角色
| 角色 | 模型 | 用途 |
|------|------|------|
| 主模型 | hy3 (TokenHub) | 论文总结、工具调用决策、搜索融合、引用生成 |
| 嵌入模型 | kinfra-text-embedding-0.6b (TokenHub) | 论文向量化、语义检索 |

全程通过 TokenHub API 调用，无本地训练/微调。

## 功能
- 论文摄入（ArXiv / 本地 PDF / 28+ 格式）
- 多源论文搜索（ArXiv + Semantic Scholar + OpenAlex + DBLP + Web）
- 本地三通道融合检索（向量 + 关键词 + 知识图谱）
- Neo4j 知识图谱与方法实体关系抽取
- 论文总结 + BibTeX + 代码查找
- Web Chat 浏览器端交互 + Dashboard 可视化看板
- 全部推理由 Hy3 完成

## Demo 演示
https://github.com/wangyue377/ResForge2/blob/rhinobird2026/media/demo/demo.mp4
