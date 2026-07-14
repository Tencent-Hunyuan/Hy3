import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

APP_TITLE = "RhinoProject Copilot"
APP_SUBTITLE = "An AI-powered open-source project planning and documentation assistant based on Hy3-preview."

BASE_DIR = Path(__file__).resolve().parent
PROMPT_DIR = BASE_DIR / "prompts"

TASK_CONFIG = {
    "Issue 解读": {"prompt_file": "issue_analyzer.md", "download_name": "issue_analysis_result.md"},
    "项目方案生成": {"prompt_file": "project_planner.md", "download_name": "project_plan_result.md"},
    "开发计划生成": {"prompt_file": "project_planner.md", "download_name": "development_plan_result.md"},
    "README 生成": {"prompt_file": "readme_generator.md", "download_name": "readme_result.md"},
    "PPT / 答辩大纲生成": {"prompt_file": "ppt_outline_generator.md", "download_name": "ppt_outline_result.md"},
    "项目质量自评": {"prompt_file": "evaluator.md", "download_name": "project_evaluation_result.md"},
}


def load_prompt(task_type: str) -> str:
    prompt_file = TASK_CONFIG[task_type]["prompt_file"]
    prompt_path = PROMPT_DIR / prompt_file
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return """你是 RhinoProject Copilot，一个面向学生开发者的 AI 开源项目实践助手。\n请根据用户输入，输出结构化、清晰、可执行的内容。"""


def build_system_prompt(task_type: str) -> str:
    base_prompt = """
你是 RhinoProject Copilot，一个面向学生开发者的 AI 开源项目实践助手。

你的目标是帮助用户理解开源 Issue、设计项目方案、拆解技术路线、生成 README、准备 PPT / 答辩大纲，并对项目质量进行自评。

输出要求：
- 主要使用中文
- 必要技术术语保留英文
- 结构清晰，分点表达
- 内容具体，不要空泛
- 不要编造不存在的事实、链接、奖项或外部数据
- 所有建议都要尽量可执行
"""
    return base_prompt + "\n\n" + load_prompt(task_type)


def get_client() -> OpenAI:
    base_url = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key = os.getenv("HY3_API_KEY", "EMPTY")
    return OpenAI(base_url=base_url, api_key=api_key)


def call_hy3(system_prompt: str, user_prompt: str) -> str:
    model_name = os.getenv("HY3_MODEL", "hy3")
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            top_p=0.9,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
        )
    except TypeError:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            top_p=0.9,
        )
    return response.choices[0].message.content


def render_sample_input() -> str:
    return """【犀牛鸟实战issue】Build a vibe-coded application powered by Hy3

问题描述：
希望看到更多基于 Hy3 的端到端应用，展示模型在真实场景中的能力。

期望改进：
参与者使用 CodeBuddy / WorkBuddy + Hy3 API，自由选题做一个端到端可运行的应用，体现 Hy3 在某个具体场景下的能力。

完成方式：
请基于活动专用分支 rhinobird2026 开发，并向该分支提交 Pull Request。

应用类型不限，下列方向可参考：
- 个人深度研究助手
- 代码评审 / PR 摘要机器人
- 多文档 RAG 问答
- 多语言翻译与语气重写工具
- 复杂任务 Agent
- 教育类自动出题 + 解析 + 错题本
- 知识图谱 / 思维导图自动生成器
- 终端命令行助手

要求：
1. 全程通过 API 调用 Hy3，不做训练、微调或本地推理部署。
2. 至少有 1 个可交互前端。
3. 至少跑通 2 个端到端 demo 流程。
4. 项目开源，README 写明 Hy3 在系统中承担的角色。
5. 鼓励在 README 中记录哪些代码块由 CodeBuddy 协作完成。

我的项目方向：
RhinoProject Copilot：基于 Hy3-preview 的学生开源项目实践助手。
它可以帮助用户解读 Issue、生成项目方案、规划开发路线、生成 README、准备 PPT / 答辩大纲，并进行项目质量自评。
"""


def render_demo_output(task_type: str) -> str:
    if task_type == "Issue 解读":
        return """## 1. 任务目标

本 Issue 要求开发者基于 Hy3-preview API 构建一个端到端可运行的 AI 应用，用真实场景展示 Hy3 在任务理解、内容生成、项目规划和多轮交互中的能力。

## 2. 完成要求

- 使用 Hy3-preview API 完成核心 AI 能力
- 至少提供一个可交互前端
- 至少跑通两个端到端 Demo 流程
- 项目代码开源
- README 说明 Hy3 在系统中的作用
- 提供示例输入、示例输出和运行方式

## 3. 技术关键词

- Hy3-preview
- OpenAI-compatible API
- Streamlit
- Prompt Templates
- Project Planning
- README Generation
- Rubric Evaluation

## 4. 推荐开发路线

1. 使用 Streamlit 搭建前端页面
2. 通过 OpenAI-compatible API 调用 Hy3-preview
3. 设计 Issue 解读、项目规划、README 生成、PPT 大纲生成、项目自评等任务模式
4. 补充 README、requirements.txt、.env.example、示例输入输出
5. 提交 Pull Request 到 rhinobird2026 分支

## 5. MVP 建议

第一版重点完成 Streamlit 前端、Hy3 API 调用、示例输入输出和完整 README，保证项目能被运行和理解。"""
    if task_type == "项目质量自评":
        return """## 1. 项目整体评价

RhinoProject Copilot 具备较完整的开源项目结构，能够围绕学生开发者参与开源训练营的真实需求，提供 Issue 解读、项目规划、README 生成、答辩大纲生成和项目质量自评等功能。

## 2. Rubric 评分表

| 评价维度 | 分数 | 评价说明 |
|---|---:|---|
| 创新性 | 8/10 | 场景明确，面向学生开源实践和竞赛项目孵化 |
| 完整度 | 8/10 | 覆盖项目从理解任务到准备交付物的完整流程 |
| 工程规范 | 8/10 | 文件结构清晰，包含依赖、配置、示例和提示词模板 |
| Hy3 使用深度 | 8/10 | Hy3 承担长文本理解、任务拆解和内容生成等核心能力 |
| 可复现性 | 8/10 | 提供 requirements.txt、.env.example 和运行命令 |
| README 完整度 | 8/10 | README 覆盖背景、功能、结构、运行方式和未来计划 |
| Demo 展示效果 | 7/10 | 已具备交互式前端，后续可补充截图或 GIF |
| 开源价值 | 8/10 | 对初次参与开源项目的学生有参考价值 |

## 3. 总分

7.9 / 10

## 4. 优化建议

- 补充 Demo 截图或 GIF
- 增加 GitHub Issue URL 自动解析
- 增加 README 或 PPT 大纲导出功能
- 增加更多真实案例测试"""
    return """## RhinoProject Copilot 生成示例

### 项目名称

RhinoProject Copilot

### 项目定位

一个面向学生开发者的开源项目实践助手，帮助用户从模糊的 Issue 或项目想法出发，生成可执行的项目方案、README、PPT 大纲和项目质量自评。

### 核心功能

- GitHub Issue 解读
- 项目方案生成
- 开发计划生成
- README 生成
- PPT / 答辩大纲生成
- 项目质量自评

### 技术栈

- Python
- Streamlit
- Hy3-preview API
- Markdown
- Prompt Templates

### 项目亮点

- 面向真实学生开源实践场景
- 强调可运行、可复现、可提交 PR
- 将 Hy3 用于长文本理解、任务拆解和文档生成
- 提供完整项目结构和示例文件"""


def render_project_description() -> None:
    st.divider()
    st.subheader("项目说明")
    st.markdown("""
RhinoProject Copilot 面向学生开发者参与开源训练营、创新创业竞赛、课程项目和科研训练等场景。

它利用 Hy3-preview 的长上下文理解、任务拆解、文档生成和 Agent 规划能力，帮助用户从一个模糊的 Issue 或项目想法出发，快速形成可执行、可展示、可开源的项目方案。
""")
    st.subheader("Rubric 评价维度")
    st.markdown("""
| 评价维度 | 说明 |
|---|---|
| 创新性 | 项目是否具有明确场景和差异化价值 |
| 完整度 | 是否形成完整功能闭环 |
| 工程规范 | 代码结构、依赖配置和项目文件是否清晰 |
| Hy3 使用深度 | Hy3 是否承担核心任务 |
| 可复现性 | 是否提供运行方式、配置文件和示例 |
| README 完整度 | 文档是否清楚说明项目背景、功能和运行方法 |
| Demo 展示效果 | 是否有可交互前端和示例输入输出 |
| 开源价值 | 是否对其他学生开发者有参考意义 |
""")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🦏", layout="wide")
    st.title("🦏 RhinoProject Copilot")
    st.caption(APP_SUBTITLE)

    with st.sidebar:
        st.header("功能选择")
        task_type = st.radio(
            "请选择生成任务",
            list(TASK_CONFIG.keys()),
            key="sidebar_task_type_radio",
        )
        st.divider()
        st.subheader("Hy3 API 配置")
        st.markdown("""
本应用通过 OpenAI-compatible API 调用 Hy3-preview。

默认环境变量：

```env
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```
""")
        st.subheader("当前任务")
        st.info(task_type)
        st.divider()
        demo_mode = st.checkbox(
            "Demo 模式：不调用 API，直接生成示例结果",
            value=True,
            key="demo_mode_checkbox",
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("输入内容")
        if st.button("填入示例 Issue", key="fill_sample_button"):
            st.session_state["user_input"] = render_sample_input()
        user_input = st.text_area(
            "请输入 GitHub Issue、项目想法、比赛主题或已有项目资料",
            value=st.session_state.get("user_input", ""),
            height=560,
            placeholder="请在这里粘贴 Issue 内容、项目想法或比赛要求...",
            key="main_input_text_area",
        )

    with col2:
        st.subheader("Hy3 生成结果")
        generate_button = st.button("生成结果", type="primary", key="generate_button")
        if generate_button:
            if not user_input.strip():
                st.warning("请先输入内容。")
            else:
                if demo_mode:
                    result = render_demo_output(task_type)
                    st.success("Demo 模式已生成示例结果。")
                    st.markdown(result)
                    st.download_button(
                        label="下载 Markdown 结果",
                        data=result,
                        file_name=TASK_CONFIG[task_type]["download_name"],
                        mime="text/markdown",
                        key="download_demo_result_button",
                    )
                else:
                    system_prompt = build_system_prompt(task_type)
                    with st.spinner("Hy3-preview 正在生成，请稍等..."):
                        try:
                            result = call_hy3(system_prompt, user_input)
                            st.markdown(result)
                            st.download_button(
                                label="下载 Markdown 结果",
                                data=result,
                                file_name=TASK_CONFIG[task_type]["download_name"],
                                mime="text/markdown",
                                key="download_api_result_button",
                            )
                        except Exception as error:
                            st.error("调用 Hy3 API 失败。请检查 API 服务、base_url、api_key 或模型名称配置。")
                            st.code(str(error))
        else:
            st.info("选择左侧功能，输入内容后点击“生成结果”。")

    render_project_description()


if __name__ == "__main__":
    main()
