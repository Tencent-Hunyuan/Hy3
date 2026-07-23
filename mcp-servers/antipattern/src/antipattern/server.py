"""AntiPattern MCP Server 入口。"""

import sys
import logging
from typing import AsyncGenerator

# Windows stdio 编码修复：防止中文输出时 ascii/gbk codec 崩溃
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from fastmcp import FastMCP

from .llm import Hy3Client, LLMError
from .schemas import ChallengeInput, RemixInput, StressInput, EscalateInput
from .strategies import registry
from .prompts import (
    build_challenge_prompt,
    build_remix_prompt,
    build_stress_prompt,
    build_escalate_prompt,
)

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("antipattern")

mcp = FastMCP(
    "AntiPattern",
    instructions="你的最佳实践，是我的异端审判对象。一个专门唱反调的设计顾问 MCP Server。",
)

_llm = Hy3Client()

# Per-tool temperature：创造性攻击 > 跨域嫁接 > 加码 > 裁判
_TEMP_CHALLENGE = 0.9
_TEMP_REMIX = 1.0
_TEMP_STRESS = 0.65
_TEMP_ESCALATE = 0.85


@mcp.tool
async def challenge_design(input: ChallengeInput) -> AsyncGenerator[str, None]:
    """对你的设计方案发起结构化叛逆挑战。

    输入你的方案（UI/架构/算法均可），AntiPattern 会：
    1. 嗅出你隐含的未验证假设
    2. 用策略库中的思维武器发起攻击
    3. 给出具体可执行的替代方案
    4. 诚实评估反方案的可行性

    intensity 1=温和质疑, 3=中度叛逆, 5=全面异端。
    """
    strategies = registry.select(
        domain=input.domain.value,
        intensity=input.intensity,
        count=2,
    )

    system, user = build_challenge_prompt(
        strategies=strategies,
        intensity=input.intensity,
        user_design=input.design,
    )

    try:
        for chunk in _llm.reason_stream(system, user, deep=True, temperature=_TEMP_CHALLENGE):
            yield chunk
    except LLMError as e:
        logger.error("challenge_design failed: %s", e)
        yield f"\n\n[AntiPattern 开炮失败] {e}\n\n请检查 HY3_BASE_URL / HY3_API_KEY 配置后重试。"
        return

    # 流结束后追加策略元信息
    names = "、".join(f"{s.name}（强度{s.intensity}）" for s in strategies)
    yield f"\n\n---\n*本次思维武器：{names}*"


@mcp.tool
async def remix_paradigm(input: RemixInput) -> AsyncGenerator[str, None]:
    """跨域嫁接：用一个完全不相关的领域重新解决你的问题。

    输入你的技术问题，AntiPattern 会从一个不相关领域
    （厨房、爵士乐、免疫系统、城市规划、军事参谋...）
    中提取核心原理，做结构化映射，给出迁移方案。

    可以指定 foreign_domain，也可以留空让 AntiPattern 自主选择最同构的领域。
    """
    system, user = build_remix_prompt(
        problem=input.problem,
        foreign_domain=input.foreign_domain,
        intensity=input.intensity,
    )

    try:
        for chunk in _llm.reason_stream(system, user, deep=True, temperature=_TEMP_REMIX):
            yield chunk
    except LLMError as e:
        logger.error("remix_paradigm failed: %s", e)
        yield f"\n\n[AntiPattern 开炮失败] {e}\n\n请检查 HY3_BASE_URL / HY3_API_KEY 配置后重试。"


@mcp.tool
async def stress_test_orthodoxy(input: StressInput) -> AsyncGenerator[str, None]:
    """对一条'行业共识'发起极端反方论证，找出它的失效边界。

    输入你信奉的最佳实践（如"微服务优于单体"、"REST 比 GraphQL 好"），
    AntiPattern 会公正地呈现正反双方最强论证，
    然后给出裁决：什么条件下成立，什么条件下是教条。
    """
    system, user = build_stress_prompt(
        orthodoxy=input.orthodoxy,
        context=input.context,
    )

    try:
        for chunk in _llm.reason_stream(system, user, deep=True, temperature=_TEMP_STRESS):
            yield chunk
    except LLMError as e:
        logger.error("stress_test_orthodoxy failed: %s", e)
        yield f"\n\n[AntiPattern 开炮失败] {e}\n\n请检查 HY3_BASE_URL / HY3_API_KEY 配置后重试。"


@mcp.tool
async def escalate(input: EscalateInput) -> AsyncGenerator[str, None]:
    """在已有反方案基础上继续加码——'还不够疯'。

    把上一轮 AntiPattern 的完整输出传入，
    它会在其基础上叠加更极端的视角和更大胆的方案。
    可以指定加码方向（如'更极端'、'换个角度'、'落地性更强'）。
    """
    system, user = build_escalate_prompt(
        previous_output=input.previous_output,
        intensity=input.intensity,
        direction=input.direction,
    )

    try:
        for chunk in _llm.reason_stream(system, user, deep=True, temperature=_TEMP_ESCALATE):
            yield chunk
    except LLMError as e:
        logger.error("escalate failed: %s", e)
        yield f"\n\n[AntiPattern 开炮失败] {e}\n\n请检查 HY3_BASE_URL / HY3_API_KEY 配置后重试。"


def main():
    """CLI 入口。"""
    mcp.run()


if __name__ == "__main__":
    main()
