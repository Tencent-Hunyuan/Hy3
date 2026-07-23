"""remix_paradigm 的 prompt 组装。"""

from ..persona import PERSONA_BASE, INTENSITY_MODIFIERS, REMIX_OUTPUT_STRUCTURE

# 跨域领域池：作为参考菜单传给 Hy3，由模型根据问题结构自主选择最同构的领域
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
    "真菌网络（菌丝体的去中心化资源路由）",
    "围棋定式（局部最优与全局势的博弈）",
    "电影蒙太奇（剪辑创造意义，而非记录意义）",
    "拍卖机制设计（激励相容与信息不对称）",
    "航海导航（不确定环境下的多信号融合决策）",
    "即兴喜剧（约束即创造力，限制即自由）",
    "生态系统演替（从先锋群落顶级群落的阶段性架构）",
    "密码学（零知识证明与最小信任假设）",
    "舞蹈编排（时间轴上的空间资源调度）",
    "考古 stratigraphy（地层叠压关系与逆向工程）",
    "交响乐配器（同一旋律在不同音色间的职责分配）",
    "消防指挥（信息不完整下的快速决策与资源预置）",
]


def build_remix_prompt(
    problem: str,
    foreign_domain: str,
    intensity: int,
) -> tuple[str, str]:
    """组装 remix_paradigm 的 system + user prompt。

    用户指定领域时直接使用；未指定时把领域池作为参考菜单传给 Hy3，
    让模型根据问题的底层结构自主选择最同构的领域（也可以超出池子）。
    """
    intensity_note = INTENSITY_MODIFIERS.get(intensity, INTENSITY_MODIFIERS[3])

    if foreign_domain.strip():
        # 用户指定了领域
        domain_instruction = f"源领域（用户指定）：{foreign_domain}"
        user_domain_note = f"用「{foreign_domain}」的原理重新解决它。认真映射，不要敷衍。"
    else:
        # 让 Hy3 自主选择
        menu = "\n".join(f"- {d}" for d in FOREIGN_DOMAINS)
        domain_instruction = f"""源领域：由你自主选择。

以下是参考领域池，但如果你认为有更合适的领域不在列表中，可以自行选择——
只要解释清楚为什么这个领域和问题在底层结构上同构（不是表面相似）。

参考池：
{menu}"""
        user_domain_note = "选一个你认为在底层结构上最同构的领域，重新解决它。先说为什么选这个领域，再展开映射。"

    system = f"""{PERSONA_BASE}

---

{intensity_note}

---

本次任务：跨域嫁接。你必须认真地将一个不相关领域的核心原理映射到用户的技术问题上。
不是表面比喻，是结构同构。找到'基本粒子'和'力'的对应关系。

{domain_instruction}

---

{REMIX_OUTPUT_STRUCTURE}"""

    user = f"""我的技术问题/设计决策：

{problem}

{user_domain_note}"""

    return system, user
