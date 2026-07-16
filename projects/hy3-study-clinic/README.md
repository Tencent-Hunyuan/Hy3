# Hy3 Study Clinic

> An evidence-grounded study workflow powered by the Hy3 API.

## 项目简介

Hy3 Study Clinic 是一个面向学习材料的可交互 Web 应用，提供从材料理解、自动出题、混合判分，到错题康复和历史掌握度更新的完整学习闭环。

完整项目以独立开源仓库的形式维护：

- **项目仓库：** [Small-fish-QAQ/hy3-study-clinic](https://github.com/Small-fish-QAQ/hy3-study-clinic)
- **完整 README：** [项目说明、架构、运行方式和限制](https://github.com/Small-fish-QAQ/hy3-study-clinic/blob/main/README.md)
- **演示视频：** [Hy3 Study Clinic Demo](https://github.com/Small-fish-QAQ/hy3-study-clinic/blob/main/docs/assets/hy3-study-clinic-demo.mp4)
- **视频时长：** 1:38.834
- **开源协议：** [Apache-2.0](https://github.com/Small-fish-QAQ/hy3-study-clinic/blob/main/LICENSE)

## 端到端流程

### 流程一：材料分析与混合判分

1. 用户导入学习材料。
2. 应用将材料切分为稳定的 source blocks。
3. Hy3 提取核心概念，并为每项内容返回对应的原文引用。
4. 应用在本地校验引用是否真实存在于指定源块。
5. Hy3 生成单选题与简答题。
6. 单选题由本地规则确定性判分，简答题由 Hy3 进行语义判分。
7. 错题被写入错题本，并更新历史掌握度。

### 流程二：错题康复

1. 应用选取当前尚未解决的错题概念。
2. Hy3 为这些概念生成针对性的康复练习。
3. 用户完成新一轮练习并再次接受混合判分。
4. 达到要求后，对应错题被标记为已解决。
5. 应用更新该材料的历史加权掌握度。

## Hy3 在系统中的职责

在线模式通过 Hy3 API 提供模型能力；项目不进行模型训练、微调或本地推理部署。

Hy3 负责：

- 基于材料的概念提取；
- 带原文依据的题目生成；
- 简答题语义判分；
- 错题康复练习生成；
- 结构化反馈与解析生成。

本地确定性代码负责：

- 学习材料切分与 source block 建立；
- 原文引用位置校验；
- 客观题判分；
- SQLite 持久化；
- 错题生命周期管理；
- 历史掌握度更新；
- 请求取消与过期响应防护；
- 历史材料恢复、重命名和永久删除。

仓库包含一个确定性的 Fake Provider，仅用于离线开发和自动化测试；最终演示流程使用真实 Hy3 API。

## 交互前端

项目包含 React + TypeScript Web 前端，支持：

- 学习材料导入；
- Hy3 在线概念分析；
- 原文依据展开查看；
- 单选题和简答题作答；
- 混合判分结果展示；
- 错题康复练习；
- 历史材料管理；
- 历史加权掌握度展示。

## CodeBuddy 协作

CodeBuddy Code 通过腾讯云 TokenHub 连接 Hy3，用于对原文证据展开组件进行一次聚焦的无障碍和回归测试审查。

本次被接受的协作贡献包括：

- 检查 `SourceEvidencePanel`、调用位置、共享类型与测试；
- 确认现有生产实现已具备原生按钮、`aria-expanded`、`aria-controls` 和稳定面板 ID；
- 修复条件渲染后测试继续引用已卸载 DOM 节点的问题；
- 增加 Enter 与 Space 键盘交互覆盖；
- 增加引用源块不可用时的安全回退测试。

CodeBuddy 未执行暂存、提交或推送操作。

## 演示与证据

最终演示视频覆盖：

- 材料导入与 Hy3 概念分析；
- 带原文依据的题目生成；
- 客观题与简答题混合判分；
- 针对错题的康复练习；
- 错题解决状态；
- 历史加权掌握度。

材料搜索、重命名和永久删除功能记录在项目仓库的配套截图中。

## 验证结果

最终本地验证结果：

| Workspace | Test files | Tests |
| --- | ---: | ---: |
| Shared | 3 | 39 |
| Server | 17 | 141 |
| Web | 2 | 46 |
| **Overall** | **22** | **226** |

此外：

- Production build：通过
- ESLint：通过
- Prettier：通过
- `git diff --check`：通过

## 安全与隐私

- 仓库中不包含真实 API Key。
- 真实凭据从被忽略的本地 `.env` 文件加载。
- SQLite、WAL 和 SHM 文件不会被提交。
- 只有在启用真实 Hy3 模式时，学习材料和判分上下文才会发送给 Hy3 API。

## 已知限制

- 页面刷新后不会重建历史测验、提交和判分结果页面。
- 尚未提交的答案草稿不会持久化。
- 每轮康复练习最多覆盖三个未解决概念。
- 永久删除材料后无法撤销。
- 掌握度是确定性的历史加权启发式指标，不是认知诊断模型。
- 严格的原文依据校验可能导致部分有用但格式不合格的模型结果需要重新生成。

## 相关 Issue

Submission for [Tencent-Hunyuan/Hy3#4](https://github.com/Tencent-Hunyuan/Hy3/issues/4).