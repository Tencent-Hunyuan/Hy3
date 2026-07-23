"""stress_test_orthodoxy 的 prompt 组装。"""

from ..persona import PERSONA_BASE, STRESS_OUTPUT_STRUCTURE


def build_stress_prompt(
    orthodoxy: str,
    context: str,
) -> tuple[str, str]:
    """组装 stress_test_orthodoxy 的 system + user prompt。"""
    system = f"""{PERSONA_BASE}

---

本次任务：对一条行业共识发起极端反方论证。

规则：
- 你不是在抬杠，你是在做压力测试
- 反方论证必须严密、有真实反例支撑
- 正方也要公正呈现（先理解为什么人们信它）
- 最终裁决必须给出明确的适用边界

---

{STRESS_OUTPUT_STRUCTURE}"""

    context_block = ""
    if context.strip():
        context_block = f"\n我的具体使用场景：{context}\n"

    user = f"""我要你压力测试的"行业共识"：

"{orthodoxy}"
{context_block}
正方反方都给我打满，然后当裁判。"""

    return system, user
