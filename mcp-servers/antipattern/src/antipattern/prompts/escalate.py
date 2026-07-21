"""escalate 的 prompt 组装。"""

from ..persona import PERSONA_BASE, INTENSITY_MODIFIERS, ESCALATE_OUTPUT_STRUCTURE


def build_escalate_prompt(
    previous_output: str,
    intensity: int,
    direction: str,
) -> tuple[str, str]:
    """组装 escalate 的 system + user prompt。"""
    intensity_note = INTENSITY_MODIFIERS.get(intensity, INTENSITY_MODIFIERS[5])

    direction_block = ""
    if direction.strip():
        direction_block = f"\n用户希望加码的方向：{direction}\n"

    system = f"""{PERSONA_BASE}

---

{intensity_note}

---

本次任务：在上一轮输出的基础上继续加码。上一轮太温和了，你需要更狠。

规则：
- 不要重复上一轮的观点，要在其基础上叠加新的攻击角度
- 反方案要比上一轮更大胆，但依然有逻辑链
- 诚实标注"疯狂边界"——哪里从大胆变成了纯疯
- 即使最疯狂的方案，也要给出最小的第一步

---

{ESCALATE_OUTPUT_STRUCTURE}"""

    user = f"""上一轮我的输出（你觉得还不够狠的那个）：

---
{previous_output}
---
{direction_block}
加码。别客气。"""

    return system, user
