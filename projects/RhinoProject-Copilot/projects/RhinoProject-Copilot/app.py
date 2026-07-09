import os
import json
import streamlit as st
from openai import OpenAI


APP_TITLE = "RhinoProject Copilot"
APP_SUBTITLE = "An AI-powered open-source project planning assistant based on Hy3-preview."


def get_client():
    """
    Hy3-preview is called through an OpenAI-compatible API endpoint.

    Environment variables:
    - HY3_BASE_URL: API base URL, default: http://127.0.0.1:8000/v1
    - HY3_API_KEY: API key, default: EMPTY
    - HY3_MODEL: model name, default: hy3
    """
    base_url = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key = os.getenv("HY3_API_KEY", "EMPTY")

    return OpenAI(
        base_url=base_url,
        api_key=api_key
    )


def call_hy3(system_prompt: str, user_prompt: str) -> str:
    model_name = os.getenv("HY3_MODEL", "hy3")
    client = get_client()

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.7,
        top_p=0.9,
        extra_body={
            "chat_template_kwargs": {
                "reasoning_effort": "high"
            }
        }
    )

    return response.choices[0].message.content


def build_system_prompt(task_type: str) -> str:
    common_role = """
You are RhinoProject Copilot, an AI assistant for student developers.
Your goal is to help users understand open-source issues, design project plans,
write README documents, prepare presentation outlines and evaluate project quality.

You should provide clear, structured, actionable and beginner-friendly output.
Use Chinese as the main language, but keep necessary technical terms in English.
Do not fabricate links, awards or external facts.
"""

    task_prompts = {
        "Issue 解读": """
You need to analyze a GitHub Issue.
Please output:
1. 任务目标
2. 任务要求
3. 技术关键词
4. 必须交付的内容
5. 难点分析
6. 推荐开发路线
7. 第一版 MVP 建议
""",
        "项目方案生成": """
You need to generate a complete project proposal.
Please output:
1. 项目名称
2. 项目定位
3. 目标用户
4. 使用场景
5. 核心功能
6. 技术栈
7. 创新点
8. 预期成果
9. 最小可行版本 MVP
""",
        "开发计划生成": """
You need to generate a practical development plan.
Please output:
1. 5-day development plan
2. Daily tasks
3. Required files
4. Testing checklist
5. Demo preparation checklist
6. Pull Request preparation checklist
""",
        "README 生成": """
You need to generate a high-quality README for an open-source project.
Please output in Markdown format:
1. Project title
2. Introduction
3. Features
4. Tech stack
5. Project structure
6. Installation
7. Usage
8. Example input and output
9. Future work
10. License
""",
        "PPT / 答辩大纲生成": """
You need to generate a presentation and defense outline.
Please output:
1. PPT page-by-page outline
2. 1-minute project introduction script
3. Demo explanation script
4. Project highlights
5. Possible questions from reviewers
6. Suggested answers
""",
        "项目质量自评": """
You need to evaluate the project with a rubric.
Please output:
1. Rubric table with scores from 1 to 10
2. Evaluation dimensions:
   - Innovation
   - Completeness
   - Engineering quality
   - Hy3 usage depth
   - Reproducibility
   - README quality
   - Demo quality
   - Open-source value
3. Overall score
4. Strengths
5. Weaknesses
6. Improvement suggestions
"""
    }

    return common_role + "\n" + task_prompts.get(task_type, "")


def render_sample_input():
    return """【犀牛鸟实战issue】Build a vibe-coded application powered by Hy3

问题描述：
希望看到更多基于 Hy3 的端到端应用，展示模型在真实场景中的能力。

期望改进：
参与者使用 CodeBuddy / WorkBuddy + Hy3 API，自由选题做一个端到端可运行的应用，体现 Hy3 在某个具体场景下的能力。

完成方式：
请基于活动专用分支 rhinobird2026 开发，并向该分支提交 Pull Request。
应用类型不限，可做个人深度研究助手、代码评审机器人、多文档 RAG 问答、多语言翻译、复杂任务 Agent、教育类自动出题、知识图谱生成器等。

要求：
1. 全程通过 API 调用 Hy3，不做训练、微调或本地推理部署。
2. 至少有 1 个可交互前端。
3. 至少跑通 2 个端到端 demo 流程。
4. 项目开源，README 写明 Hy3 在系统中承担的角色。
5. 鼓励在 README 中记录哪些代码块由 CodeBuddy 协作完成。
"""


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🦏",
        layout="wide"
    )

    st.title("🦏 RhinoProject Copilot")
    st.caption(APP_SUBTITLE)

    with st.sidebar:
        st.header("功能选择")
        task_type = st.radio(
            "请选择生成任务",
            [
                "Issue 解读",
                "项目方案生成",
                "开发计划生成",
                "README 生成",
                "PPT / 答辩大纲生成",
                "项目质量自评"
            ]
        )

        st.divider()
        st.subheader("Hy3 API 配置说明")
        st.markdown(
            """
            本应用通过 OpenAI-compatible API 调用 Hy3-preview。

            默认配置：
            - `HY3_BASE_URL=http://127.0.0.1:8000/v1`
            - `HY3_API_KEY=EMPTY`
            - `HY3_MODEL=hy3`
            """
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("输入内容")

        if st.button("填入示例 Issue"):
            st.session_state["user_input"] = render_sample_input()

        user_input = st.text_area(
            "请输入 GitHub Issue、项目想法、比赛主题或已有项目资料",
            value=st.session_state.get("user_input", ""),
            height=520,
            placeholder="请在这里粘贴 Issue 内容或项目想法..."
        )

    with col2:
        st.subheader("Hy3 生成结果")

        if st.button("生成结果", type="primary"):
            if not user_input.strip():
                st.warning("请先输入内容。")
            else:
                system_prompt = build_system_prompt(task_type)
                with st.spinner("Hy3-preview 正在生成，请稍等..."):
                    try:
                        result = call_hy3(system_prompt, user_input)
                        st.markdown(result)

                        st.download_button(
                            label="下载 Markdown 结果",
                            data=result,
                            file_name=f"{task_type}_result.md",
                            mime="text/markdown"
                        )

                    except Exception as e:
                        st.error("调用 Hy3 API 失败。请检查 API 服务、base_url、api_key 或模型名称配置。")
                        st.code(str(e))

        else:
            st.info("选择左侧功能，输入内容后点击“生成结果”。")

    st.divider()
    st.subheader("项目说明")
    st.markdown(
        """
        RhinoProject Copilot 面向学生开发者参与开源训练营、创新创业竞赛、课程项目和科研训练等场景。
        它利用 Hy3-preview 的长上下文理解、任务拆解、文档生成和 Agent 规划能力，
        帮助用户从一个模糊的 Issue 或项目想法出发，快速形成可执行、可展示、可开源的项目方案。
        """
    )


if __name__ == "__main__":
    main()
