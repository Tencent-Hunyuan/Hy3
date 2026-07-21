"""策略数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Strategy:
    """单条叛逆策略。"""
    id: str
    domain: str  # "ui" | "architecture" | "general"
    name: str
    provocation: str  # 注入 prompt 的核心挑衅语句
    thinking_frame: str  # 要求模型采用的思维框架
    intensity: int  # 1-5
    tags: list[str] = field(default_factory=list)
