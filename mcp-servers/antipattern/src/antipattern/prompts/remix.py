"""remix_paradigm 的 prompt 组装。"""

import random

from ..persona import PERSONA_BASE, INTENSITY_MODIFIERS, REMIX_OUTPUT_STRUCTURE

# 预设的跨域领域池（用户未指定时随机抽取）
FOREIGN_DOMAINS = [
    "厨房 brigade 系统（米其林后厨的分工与节奏）",
    "爵士乐即兴（和弦约束下的自由）",
    "免疫系统（分布式识别与记忆）",
    "城市规划（有机生长 vs 顶层设计）",
    "进化生物学（适应度景观与自然选择）",
    "军事参谋体系（OODA 循环与任务式指挥）",
    "日本园林设计（留白与借景）",
    "期货市场（价格发现与风险分散）",
    "戏剧即兴表演（Yes, and... 原则）",
    "蚁群算法（无中心协调的集体智能）",
    "急诊医学（分诊与资源极端约束）",
    "建筑改造（在旧结构上加新功能的约束美学）",
]


def build_remix_prompt(
    problem: str,
    foreign_domain: str,
    intensity: int,
) -> tuple[str, str]:
    """组装 remix_paradigm 的 system + user prompt。"""
    if not foreign_domain.strip():
        foreign_domain = random.choice(FOREIGN_DOMAINS)

    intensity_note = INTENSITY_MODIFIERS.get(intensity, INTENSITY_MODIFIERS[3])

    system = f"""{PERSONA_BASE}

---

{intensity_note}

---

本次任务：跨域嫁接。你必须认真地将一个不相关领域的核心原理映射到用户的技术问题上。
不是表面比喻，是结构同构。找到'基本粒子'和'力'的对应关系。

源领域：{foreign_domain}

---

{REMIX_OUTPUT_STRUCTURE}"""

    user = f"""我的技术问题/设计决策：

{problem}

用「{foreign_domain}」的原理重新解决它。认真映射，不要敷衍。"""

    return system, user
