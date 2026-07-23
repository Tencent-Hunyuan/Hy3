"""challenge_design 的 prompt 组装。"""

from ..persona import PERSONA_BASE, INTENSITY_MODIFIERS, get_challenge_structure
from ..strategies.registry import Strategy


def build_challenge_prompt(
    strategies: list[Strategy],
    intensity: int,
    user_design: str,
) -> tuple[str, str]:
    """组装 challenge_design 的 system + user prompt。

    Returns:
        (system_prompt, user_prompt)
    """
    # 策略注入
    strategy_lines = []
    for i, s in enumerate(strategies, 1):
        strategy_lines.append(f"{i}. 【{s.name}】{s.provocation}")
        strategy_lines.append(f"   思维框架：{s.thinking_frame}")

    strategies_block = "\n".join(strategy_lines)
    intensity_note = INTENSITY_MODIFIERS.get(intensity, INTENSITY_MODIFIERS[3])
    output_structure = get_challenge_structure(intensity)

    system = f"""{PERSONA_BASE}

---

{intensity_note}

---

本次挑战使用以下思维武器：

{strategies_block}

---

{output_structure}"""

    user = f"""以下是我要你挑战的设计方案：

{user_design}

开炮。"""

    return system, user
