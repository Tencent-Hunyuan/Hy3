"""通用跨域叛逆策略。"""

from .models import Strategy

GENERAL_STRATEGIES: list[Strategy] = [
    Strategy(
        id="gen.cross_graft",
        domain="general",
        name="跨域嫁接",
        provocation=(
            "用一个完全不相关的领域的核心原理来重新解决这个问题。"
            "不是表面类比，是结构映射：那个领域的'基本粒子'对应你这边的什么？"
            "那个领域的'力'对应你这边的什么？"
        ),
        thinking_frame="结构类比：有效的跨域迁移不是'像'，是'同构'。找到数学/逻辑层面的同构。",
        intensity=3,
        tags=["跨域", "类比", "结构"],
    ),
    Strategy(
        id="gen.role_hijack",
        domain="general",
        name="角色劫持",
        provocation=(
            "如果这个技术决策由一个完全不同背景的人来做——"
            "朋克乐队主唱、幼儿园老师、军事参谋、急诊科医生、街头小贩——"
            "他们会问什么你从来没问过的问题？他们会做什么你'不敢'做的选择？"
        ),
        thinking_frame="认知多样性：专业训练既是能力也是盲区。外行的'蠢问题'往往是内行的盲区。",
        intensity=3,
        tags=["角色", "视角", "盲区"],
    ),
    Strategy(
        id="gen.incentive_flip",
        domain="general",
        name="激励反转",
        provocation=(
            "如果做好这件事的奖励指标完全反转——不是'更快'而是'更慢但更深'、"
            "不是'更多用户'而是'更少但更狂热'、不是'更少 bug'而是'更多有趣的 bug'——"
            "你的方案会怎么变？这揭示了你在优化什么、忽略了什么。"
        ),
        thinking_frame="激励设计：你优化什么就得到什么。但你在优化的那个指标，真的是目标吗？",
        intensity=4,
        tags=["激励", "指标", "反转"],
    ),
    Strategy(
        id="gen.first_principles",
        domain="general",
        name="第一性原理暴力拆解",
        provocation=(
            "忘掉所有现有方案、所有行业惯例、所有'大家都这么做'。"
            "从物理定律、数学原理、人性最基本的需求出发，重新推导。"
            "如果这个问题今天第一次被提出，没有任何历史包袱，答案会是什么？"
        ),
        thinking_frame="第一性原理：类比思维是效率工具，也是创新的最大障碍。回到公理层。",
        intensity=5,
        tags=["第一性", "公理", "重建"],
    ),
    Strategy(
        id="gen.analogy_break",
        domain="general",
        name="类比断裂",
        provocation=(
            "找到你的方案所依赖的核心类比（'微服务像城市'、'数据像石油'、"
            "'代码像建筑'），然后精确指出这个类比在哪里失效。"
            "类比失效的地方，就是你的方案最脆弱的地方。"
        ),
        thinking_frame="类比审计：所有设计决策都基于类比。类比不是真理，是有边界的近似。",
        intensity=3,
        tags=["类比", "边界", "脆弱"],
    ),
    Strategy(
        id="gen.survivorship",
        domain="general",
        name="幸存者偏差",
        provocation=(
            "你参考的那些成功案例——做了同样选择但失败了的团队在哪里？"
            "他们的尸体上写着什么教训？你凭什么觉得自己不是那个分母？"
            "不是让你不做，是让你知道你在赌什么。"
        ),
        thinking_frame="概率思维：成功故事是采样偏差。决策质量要看分布，不是看个例。",
        intensity=4,
        tags=["偏差", "概率", "风险"],
    ),
]
