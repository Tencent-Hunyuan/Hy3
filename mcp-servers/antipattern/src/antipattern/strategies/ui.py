"""UI/前端叛逆策略。"""

from .models import Strategy

UI_STRATEGIES: list[Strategy] = [
    Strategy(
        id="ui.constraint_inversion",
        domain="ui",
        name="约束反转",
        provocation=(
            "如果用户方案中最核心的那个 UI 元素/交互模式被完全禁止使用，"
            "你怎么传达同样的信息？不是'替代'，是'从根本上重新思考信息传达方式'。"
        ),
        thinking_frame="从信息论角度思考：用户真正需要接收的是什么信息？当前 UI 是传达该信息的唯一路径吗？",
        intensity=3,
        tags=["反转", "信息论", "极简"],
    ),
    Strategy(
        id="ui.sensory_swap",
        domain="ui",
        name="感官替代",
        provocation=(
            "如果这个界面只能通过声音、触觉或空间位置来交互（完全不能用视觉），"
            "你会怎么设计？然后反过来想：这个非视觉方案里有什么洞察可以反哺视觉设计？"
        ),
        thinking_frame="多感官设计思维：每种感官通道有什么独特的信息编码优势？视觉霸权遮蔽了什么？",
        intensity=4,
        tags=["感官", "无障碍", "跨模态"],
    ),
    Strategy(
        id="ui.era_displacement",
        domain="ui",
        name="时代错位",
        provocation=(
            "用另一个时代的设计语言重新设计这个界面：1985 年的 DOS 终端、"
            "1920 年的包豪斯海报、2077 年的空间计算、或者 1995 年的 GeoCities。"
            "那个时代的设计约束里藏着什么被遗忘的智慧？"
        ),
        thinking_frame="设计考古学：每个时代的设计都是对当时技术约束的最优解。约束变了，但人性没变。",
        intensity=2,
        tags=["时代", "美学", "约束"],
    ),
    Strategy(
        id="ui.extreme_user",
        domain="ui",
        name="极端用户",
        provocation=(
            "为最极端的用户重新设计：戴厚手套的宇航员、5 岁小孩、帕金森患者、"
            "在颠簸地铁上单手持机的上班族、或者一个故意搞破坏的熊孩子。"
            "为极端用户做的设计往往对普通用户更好。"
        ),
        thinking_frame="包容性设计的极端化：如果你为最受限的用户设计，普通用户会获得什么额外好处？",
        intensity=3,
        tags=["用户", "包容性", "极端"],
    ),
    Strategy(
        id="ui.taboo_list",
        domain="ui",
        name="禁忌清单",
        provocation=(
            "列出这个 UI 领域里'绝对没人敢做'的 5 件事（比如：没有导航栏、"
            "故意让用户迷路、用红色表示成功、没有撤销、界面会'死'）。"
            "然后逐一论证：在什么条件下，这个禁忌其实是天才设计？"
        ),
        thinking_frame="禁忌考古：每个设计禁忌背后都有一个历史事故。但历史条件还成立吗？",
        intensity=5,
        tags=["禁忌", "极端", "反转"],
    ),
    Strategy(
        id="ui.emotion_hijack",
        domain="ui",
        name="情绪劫持",
        provocation=(
            "如果这个界面的首要设计目标不是'效率'或'易用'，而是让用户产生一种"
            "强烈的情绪（敬畏、紧张、孤独、狂喜、怀旧），你会怎么改？"
            "情绪记忆比功能记忆持久 10 倍。"
        ),
        thinking_frame="情感设计：Don Norman 的三层模型（本能/行为/反思）中，你的方案卡在哪一层？",
        intensity=4,
        tags=["情绪", "记忆", "叙事"],
    ),
    Strategy(
        id="ui.destruction_test",
        domain="ui",
        name="破坏测试",
        provocation=(
            "如果用户会故意'破坏'这个界面（乱点、输入垃圾数据、疯狂刷新、"
            "断网重连），怎么设计让'破坏'本身成为体验的一部分？"
            "游戏里'死亡'是乐趣，为什么软件里'错误'只能是惩罚？"
        ),
        thinking_frame="游戏设计思维：失败状态可以是有趣的。错误恢复可以是叙事的一部分。",
        intensity=5,
        tags=["破坏", "游戏化", "容错"],
    ),
    Strategy(
        id="ui.minimal_violence",
        domain="ui",
        name="极简暴力",
        provocation=(
            "这个界面里只能保留一个元素，其他全部删除。你留哪个？为什么？"
            "然后：只靠这一个元素，能不能完成 80% 的核心任务？"
        ),
        thinking_frame="本质追问：剥掉所有装饰和惯例后，这个产品的原子价值是什么？",
        intensity=2,
        tags=["极简", "本质", "删减"],
    ),
]
