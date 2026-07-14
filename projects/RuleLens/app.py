"""RuleLens · 规则透镜 — Streamlit 主入口。

仅负责启动 UI；所有业务逻辑位于 ``src/rulelens`` 包内，不依赖 Streamlit，可独立测试。
"""

from rulelens.ui import render_app

if __name__ == "__main__":
    render_app()
