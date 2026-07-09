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
    "Issue 解读": {
        "prompt_file": "issue_analyzer.md",
        "download_name": "issue_analysis_result.md",
    },
    "项目方案生成": {
        "prompt_file": "project_planner.md",
        "download_name": "project_plan_result.md",
    },
    "开发计划生成": {
        "prompt_file": "project_planner.md",
        "download_name": "development_plan_result.md",
    },
    "README 生成": {
        "prompt_file": "readme_generator.md",
        "download_name": "readme_result.md",
    },
    "PPT / 答辩大纲生成": {
        "prompt_file": "ppt_outline_generator.md",
        "download_name": "ppt_outline_result.md",
    },
    "项目质量自评": {
        "prompt_file": "evaluator.md",
        "download_name": "project_evaluation_result.md",
    },
}


DEFAULT_PROMPTS = {
    "Issue 解读": """
你是 RhinoProject Copilot，一个面向学生开发者的开源项目实践助手。

请分析用户输入的 GitHub Issue，并输出以下内容：

## 1. 任务目标
用简单清晰的话说明这个 Issue 想让开发者完成什么。

## 2. 完成要求
列出必须完成的功能、文件、Demo、README、PR 等要求。

## 3. 技术关键词
提取 Issue 中涉及的关键技术。

## 4. 交付物清单
列出最终需要提交的内容。

## 5. 难点分析
分析该 Issue 对初学者来说可能困难的地方。

## 6. 推荐开发路线
给出从 0 到 1 的开发步骤。

## 7. MVP 建议
给出最小可行版本，避免项目一开始做得过大。
""",
    "项目方案生成": """
你是 RhinoProject Copilot，一个面向学生开发者的开源项目规划助手。

请根据用户输入的项目想法、比赛主题、GitHub Issue 或已有项目资料，生成一份完整、清晰、可执行的项目方案。

请输出：

## 1. 项目名称
## 2. 项目定位
## 3. 目标用户
## 4. 使用场景
## 5. 核心功能
## 6. 技术栈
## 7. 项目亮点
## 8. MVP 最小可行版本
## 9. 可扩展方向
## 10. 预期成果
""",
    "开发计划生成": """
你是 RhinoProject Copilot，一个项目开发计划生成助手。

请根据用户输入的项目资料，生成一个实际可执行的开发计划。

请输出：

## 1. 总体开发目标
## 2. 5 天开发计划
## 3. 每日任务拆解
## 4. 必须创建的文件
## 5. 测试清单
## 6. Demo 准备清单
## 7. Pull Request 提交清单
""",
    "README 生成": """
你是 RhinoProject Copilot，一个开源项目 README 文档生成助手。

请根据用户输入的项目想法、GitHub Issue、技术栈和功能描述，生成一份结构完整、适合 GitHub 开源仓库展示的 README.md。

请使用 Markdown 格式输出，并包含：

## 1. Project Title
## 2. Introduction
## 3. Features
## 4. Tech Stack
## 5. Project Structure
## 6. Installation
## 7. Configuration
## 8. Usage
## 9. Example Input and Output
## 10. Hy3-preview Role
## 11. Future Work
## 12. License
""",
    "PPT / 答辩大纲生成": """
你是 RhinoProject Copilot，一个项目展示与答辩材料生成助手。

请根据用户输入的项目简介、GitHub Issue、技术方案或已有项目资料，生成适合开源项目展示、课程答辩或竞赛路演的 PPT 大纲和答辩讲稿。

请输出：

## 1. PPT 总体定位
## 2. PPT 页面大纲
## 3. 一分钟项目介绍稿
## 4. Demo 演示讲稿
## 5. 项目亮点总结
## 6. 评委可能追问
## 7. 回答参考
## 8. 展示材料检查清单
""",
    "项目质量自评": """
你是 RhinoProject Copilot，一个开源项目质量评估助手。

请根据用户输入的项目介绍、README、GitHub Issue、技术方案或 Demo 描述，对项目进行结构化评价。

请输出：

## 1. 项目整体评价

## 2. Rubric 评分表

| 评价维度 | 分数 | 评价说明 |
|---|---:|---|
| 创新性 | /10 | 说明项目是否有明确场景和差异化价值 |
| 完整度 | /10 | 说明功能是否形成完整闭环 |
| 工程规范 | /10 | 说明目录结构、代码组织、依赖配置是否清晰 |
| Hy3 使用深度 | /10 | 说明 Hy3 是否承担核心任务，而不是只做普通聊天 |
| 可复现性 | /10 | 说明是否提供 requirements、配置说明、运行命令和示例 |
| README 完整度 | /10 | 说明 README 是否覆盖背景、功能、技术栈、运行方式和示例 |
| Demo 展示效果 | /10 | 说明是否有可交互前端、示例输入输出、截图或视频 |
| 开源价值 | /10 | 说明是否对其他学生开发者或开源社区有参考价值 |

## 3. 总分
## 4. 优势总结
## 5. 风险与不足
## 6. 优化建议
## 7. PR 提交前检查清单
""",
}


def load_prompt(task_type: str) -> str:
    prompt_file = TASK_CONFIG[task_type]["prompt_file"]
    prompt_path = PROMPT_DIR / prompt_file

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    return DEFAULT_PROMPTS.get(task_type, "")


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

    task_prompt = load_prompt(task_type)
    return base_prompt + "\n\n" + task_prompt


def get_client() -> OpenAI:
    base_url = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key = os.getenv("HY3_API_KEY", "EMPTY")

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


def call_hy3(system_prompt: str, user_prompt: str) -> str:
    model_name = os.getenv("HY3_MODEL", "hy3")
    client = get_client()

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            top_p=0.9,
            extra_body={
                "chat_template_kwargs": {
                    "reasoning_effort": "high"
                }
            },
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


def render_project_description() -> None:
    st.divider()

    st.subheader("项目说明")
    st.markdown(
        """
RhinoProject Copilot 面向学生开发者参与开源训练营、创新创业竞赛、课程项目和科研训练等场景。

它利用 Hy3-preview 的长上下文理解、任务拆解、文档生成和 Agent 规划能力，帮助用户从一个模糊的 Issue 或项目想法出发，快速形成可执行、可展示、可开源的项目方案。
        """
    )

    st.subheader("Rubric 评价维度")
    st.markdown(
        """
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
        """
    )


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🦏",
        layout="wide",
    )

    st.title("🦏 RhinoProject Copilot")
    st.caption(APP_SUBTITLE)

    with st.sidebar:
        st.header("功能选择")

        task_type = st.radio(
            "请选择生成任务",
            list(TASK_CONFIG.keys()),
        )

        st.divider()

        st.subheader("Hy3 API 配置")
        st.markdown(
            """
本应用通过 OpenAI-compatible API 调用 Hy3-preview。

默认环境变量：

```env
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```
            """
        )

        st.subheader("当前任务")
        st.info(task_type)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("输入内容")

        if st.button("填入示例 Issue"):
            st.session_state["user_input"] = render_sample_input()

        user_input = st.text_area(
            "请输入 GitHub Issue、项目想法、比赛主题或已有项目资料",
            value=st.session_state.get("user_input", ""),
            height=560,
            placeholder="请在这里粘贴 Issue 内容、项目想法或比赛要求...",
        )

    with col2:
        st.subheader("Hy3 生成结果")

        generate_button = st.button("生成结果", type="primary")

        if generate_button:
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
                            file_name=TASK_CONFIG[task_type]["download_name"],
                            mime="text/markdown",
                        )

                    except Exception as error:
                        st.error("调用 Hy3 API 失败。请检查 API 服务、base_url、api_key 或模型名称配置。")
                        st.code(str(error))
        else:
            st.info("选择左侧功能，输入内容后点击“生成结果”。")

    render_project_description()


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
