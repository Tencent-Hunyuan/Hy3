# Sample Output

## 1. Issue 解读

### 任务目标

本 Issue 要求开发者基于 Hy3-preview API 构建一个端到端可运行的 AI 应用，用真实场景展示 Hy3 在长上下文理解、任务拆解、文档生成、Agent 规划和多轮交互中的能力。

### 完成要求

- 使用 Hy3-preview API 完成核心生成能力
- 构建一个可交互前端
- 提供至少两个端到端 Demo 流程
- 项目代码开源
- README 中说明 Hy3 在系统中的作用
- 提供运行方式、示例输入输出和演示材料

### 技术关键词

- Hy3-preview API
- Streamlit
- OpenAI-compatible API
- Agent Workflow
- README Generation
- Project Planning
- Rubric Evaluation

### 推荐开发路线

1. 使用 Streamlit 搭建交互式 Web 页面
2. 使用 OpenAI-compatible API 接入 Hy3-preview
3. 设计多个任务模式，包括 Issue 解读、项目方案生成、README 生成和项目质量自评
4. 准备示例输入与示例输出
5. 完善 README、运行说明和 Demo 展示材料

---

## 2. 项目方案生成

### 项目名称

RhinoProject Copilot

### 项目定位

一个面向学生开发者的开源项目实践与竞赛项目孵化助手。

### 目标用户

- 初次参与开源项目的大学生
- 参加创新创业竞赛的学生团队
- 需要完成课程项目或科研训练的学生
- 需要撰写 README、PPT、答辩稿的项目负责人

### 核心功能

- GitHub Issue 解读
- 项目方案生成
- 技术路线拆解
- 开发计划生成
- README 文档生成
- PPT / 答辩大纲生成
- 项目质量自评

### 技术栈

- Python
- Streamlit
- Hy3-preview API
- Markdown
- JSON

### 项目亮点

- 不是普通聊天机器人，而是面向项目开发全流程的 AI Copilot
- 能从模糊想法生成可执行项目方案
- 能辅助学生完成开源训练营和竞赛项目材料
- 强调 README、Demo、PR 和答辩等真实交付物
- 通过 rubric 帮助用户自查项目质量

---

## 3. 开发计划生成

### Day 1：项目初始化

- 创建项目目录
- 编写 README
- 配置 requirements.txt
- 编写 .env.example
- 准备示例 Issue 输入

### Day 2：核心应用开发

- 使用 Streamlit 搭建 Web 页面
- 设计任务选择组件
- 编写 Hy3 API 调用函数
- 完成 Issue 解读与项目方案生成

### Day 3：文档与答辩模块

- 增加 README 生成模块
- 增加 PPT / 答辩大纲模块
- 增加项目质量自评模块
- 支持 Markdown 结果下载

### Day 4：示例与测试

- 准备 sample_issue.md
- 准备 sample_output.md
- 测试不同输入下的输出效果
- 修复异常提示和空输入问题

### Day 5：开源提交

- 完善 README 运行说明
- 添加 Demo 截图或 GIF
- 整理 PR 描述
- 提交 Pull Request 到 rhinobird2026 分支

---

## 4. 项目质量自评

| 评价维度 | 分数 | 说明 |
|---|---:|---|
| 创新性 | 8/10 | 将 Hy3 用于开源项目实践和竞赛孵化场景，具有明确目标用户 |
| 完整度 | 8/10 | 覆盖 Issue 解读、项目规划、README、PPT 和自评等多个模块 |
| 工程规范 | 7/10 | 项目结构清晰，但后续可加入更多模块化文件 |
| Hy3 使用深度 | 8/10 | Hy3 承担长文本理解、任务拆解和文档生成等核心能力 |
| 可复现性 | 8/10 | 提供 requirements.txt、.env.example 和示例输入输出 |
| README 完整度 | 8/10 | 包含项目背景、功能、技术栈、结构和计划 |
| Demo 展示效果 | 7/10 | 已具备可交互前端，后续可补充视频或 GIF |
| 开源价值 | 8/10 | 可帮助更多学生开发者理解和完成开源项目任务 |

### Overall Score

7.75 / 10

### 改进建议

- 增加 GitHub Issue 链接自动抓取功能
- 增加多轮项目优化功能
- 增加 README 和 PPT 大纲导出能力
- 增加更多真实项目案例
- 增加 Demo GIF 或短视频
