"""Streamlit Session State 管理。

状态机：EMPTY -> EXTRACTED -> ANALYZED -> QUIZ_ACTIVE -> COMPLETED。
- 重置时清理字段，不修改 .env 或示例文件；
- 不把 SDK Client 或无法序列化对象放入 Session；
- Widget key 使用稳定、带命名空间的字符串。
"""

from __future__ import annotations

import hashlib

import streamlit as st


# 阶段常量（字符串，便于与 Session 比较）
class Stage:
    EMPTY = "EMPTY"
    EXTRACTED = "EXTRACTED"
    ANALYZED = "ANALYZED"
    QUIZ_ACTIVE = "QUIZ_ACTIVE"
    COMPLETED = "COMPLETED"


DEFAULT_STATE: dict = {
    "stage": Stage.EMPTY,
    "file_name": None,
    "file_sha256": None,
    "file_bytes": None,
    "bundle": None,
    "current_scenario_index": 0,
    "selected_verdict": None,
    "attempts_by_scenario": {},
    "last_error": None,
    "_pending_sample": None,
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def init_state() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_state() -> None:
    """清空分析结果与答题状态；保留上传控件中的文件由调用方处理。"""
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value


def load_file(file_name: str, file_bytes: bytes) -> None:
    """载入新文件：写入字节并清空旧的分析 / 答题状态。"""
    st.session_state["file_name"] = file_name
    st.session_state["file_sha256"] = _sha256(file_bytes)
    st.session_state["file_bytes"] = file_bytes
    st.session_state["bundle"] = None
    st.session_state["current_scenario_index"] = 0
    st.session_state["selected_verdict"] = None
    st.session_state["attempts_by_scenario"] = {}
    st.session_state["last_error"] = None
    st.session_state["stage"] = Stage.EXTRACTED


def get_state():
    return st.session_state
