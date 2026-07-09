# RhinoProject Copilot

RhinoProject Copilot is an AI-powered open-source project planning and documentation assistant based on Hy3-preview.

## 项目简介

RhinoProject Copilot 是一个基于 Hy3-preview API 构建的学生开源项目实践助手，面向大学生参与开源训练营、创新创业竞赛、课程项目和科研训练等场景。

用户可以输入 GitHub Issue、项目想法、比赛主题或已有项目资料，系统将自动生成：

- GitHub Issue 解读
- 项目方案生成
- 技术路线拆解
- 开发任务规划
- README 文档生成
- PPT / 答辩大纲生成
- 项目质量自评

本项目希望帮助学生开发者从“看不懂任务”到“完成可展示、可开源、可答辩的项目”。

## 背景与动机

在开源训练营和创新竞赛中，很多学生开发者并不是没有想法，而是不知道如何把一个模糊任务拆解成可以执行的项目。

常见问题包括：

- 看不懂 GitHub Issue 的真实要求
- 不知道如何设计项目结构
- 不会写 README 和技术文档
- 不会拆解开发计划
- 不知道如何准备答辩 PPT 和演示视频
- 不清楚自己的项目质量是否达到提交标准

Hy3-preview 具备较强的长上下文理解、代码生成、Agent 任务拆解和复杂文本生成能力，因此适合用于构建一个面向学生开发者的项目实践助手。官方任务也要求基于 Hy3-preview 构建可运行 AI 应用，并提交 README、示例和 Demo。:contentReference[oaicite:0]{index=0}

## 核心功能

### 1. GitHub Issue 解读

输入 GitHub Issue 内容后，系统会自动分析：

- 任务目标
- 完成要求
- 技术关键词
- 交付物
- 难点分析
- 推荐开发路线

### 2. 项目方案生成

根据用户输入的项目想法或比赛主题，生成：

- 项目名称
- 应用场景
- 目标用户
- 核心功能
- 技术栈
- 创新点
- 预期成果

### 3. 开发计划生成

系统会将项目拆解为可执行任务，例如：

- Day 1：环境搭建与 API 调用
- Day 2：核心功能开发
- Day 3：前端页面与交互优化
- Day 4：README、示例输出与 Demo 视频
- Day 5：测试、优化与 PR 提交

### 4. README 生成

系统可以自动生成开源项目 README，包括：

- 项目简介
- 功能介绍
- 技术栈
- 安装方式
- 运行方式
- 项目结构
- 使用示例
- 未来计划
- 贡献说明

### 5. PPT / 答辩大纲生成

系统可以生成项目展示材料，包括：

- 路演 PPT 大纲
- 答辩讲稿
- 项目亮点总结
- 评委可能追问
- 回答参考

### 6. 项目质量自评

系统会基于 rubric 对项目进行评分：

- 创新性
- 完整度
- 工程规范
- Hy3 使用深度
- 可复现性
- README 完整度
- Demo 展示效果
- 开源价值

## 技术栈

- Python
- Streamlit
- Hy3-preview API
- Markdown
- JSON
- GitHub

## 项目结构

```text
RhinoProject-Copilot/
├── app.py
├── hy3_client.py
├── prompts/
│   ├── issue_analyzer.md
│   ├── project_planner.md
│   ├── readme_generator.md
│   ├── ppt_outline_generator.md
│   └── evaluator.md
├── examples/
│   ├── sample_issue.md
│   ├── sample_project_plan.md
│   ├── sample_readme.md
│   └── sample_evaluation.md
├── requirements.txt
└── README.md
```

## Hy3-preview 在本项目中的作用

Hy3-preview 主要承担以下能力：

- 长文本 Issue 理解
- 多步骤任务拆解
- 项目方案生成
- README 与文档生成
- 答辩材料生成
- 项目质量评价
- 面向学生开发者的交互式项目指导

## 预期效果

用户输入一个开源 Issue 后，系统可以输出一套完整项目方案，帮助用户快速理解任务、规划开发路线并准备开源提交材料。

## 后续计划

- 增加 GitHub Issue 链接自动解析
- 增加 README 一键导出功能
- 增加 PPT 大纲导出功能
- 增加项目评分可视化
- 增加多轮对话式项目优化功能
- 支持更多开源项目和竞赛场景

## License

Apache License 2.0
