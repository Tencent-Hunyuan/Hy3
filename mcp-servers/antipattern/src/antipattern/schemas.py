"""输入输出数据模型。"""

from enum import Enum
from pydantic import BaseModel, Field


class Domain(str, Enum):
    """挑战领域。"""
    UI = "ui"
    ARCHITECTURE = "architecture"
    GENERAL = "general"


class ChallengeInput(BaseModel):
    """challenge_design 工具输入。"""
    design: str = Field(
        min_length=1, max_length=8000,
        description="你的设计方案描述（越具体越好）"
    )
    domain: Domain = Field(default=Domain.GENERAL, description="方案所属领域")
    intensity: int = Field(default=3, ge=1, le=5, description="叛逆强度 1-5")


class RemixInput(BaseModel):
    """remix_paradigm 工具输入。"""
    problem: str = Field(
        min_length=1, max_length=8000,
        description="你要解决的技术问题或设计决策"
    )
    foreign_domain: str = Field(
        default="", max_length=200,
        description="用于跨域嫁接的领域（留空则由 AntiPattern 随机选择）"
    )
    intensity: int = Field(default=3, ge=1, le=5, description="叛逆强度 1-5")


class StressInput(BaseModel):
    """stress_test_orthodoxy 工具输入。"""
    orthodoxy: str = Field(
        min_length=1, max_length=4000,
        description="一条你信奉的'行业共识'或'最佳实践'"
    )
    context: str = Field(default="", max_length=4000, description="你的具体使用场景（可选）")


class EscalateInput(BaseModel):
    """escalate 工具输入。"""
    previous_output: str = Field(
        min_length=1, max_length=16000,
        description="上一轮 AntiPattern 的完整输出"
    )
    intensity: int = Field(default=5, ge=1, le=5, description="加码后的目标强度")
    direction: str = Field(
        default="", max_length=500,
        description="希望加码的方向（如'更极端'、'换个角度'、'落地性更强'）"
    )
