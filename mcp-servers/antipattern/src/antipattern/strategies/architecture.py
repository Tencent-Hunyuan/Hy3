"""架构/算法叛逆策略。"""

from .models import Strategy

ARCH_STRATEGIES: list[Strategy] = [
    Strategy(
        id="arch.complexity_inversion",
        domain="architecture",
        name="复杂度反转",
        provocation=(
            "如果 O(n²) 暴力解、全局变量、单文件 10000 行其实是正解呢？"
            "在什么规模/场景下，'优雅'的抽象反而是负债？"
            "给出一个具体的阈值：低于这个规模，暴力就是最优。"
        ),
        thinking_frame="复杂度经济学：抽象有成本。过早优化是万恶之源，但过早抽象也是。",
        intensity=2,
        tags=["复杂度", "简单", "规模"],
    ),
    Strategy(
        id="arch.paradigm_jump",
        domain="architecture",
        name="范式跳跃",
        provocation=(
            "用完全不同的计算范式重新建模这个问题：游戏引擎的 ECS 架构、"
            "编译器的多趟扫描、免疫系统的分布式识别、市场经济的价格信号、"
            "或者爵士乐的即兴规则。选一个，认真映射。"
        ),
        thinking_frame="范式迁移：不同领域解决'复杂性'的元策略是什么？哪些可以跨域复用？",
        intensity=4,
        tags=["范式", "跨域", "建模"],
    ),
    Strategy(
        id="arch.delete_test",
        domain="architecture",
        name="删除测试",
        provocation=(
            "砍掉你架构中最'理所当然'的那个组件/层/抽象。"
            "系统会退化到什么程度？这个退化真的不可接受吗？"
            "还是说你只是'习惯了'它的存在？"
        ),
        thinking_frame="切斯特顿之篱：在你拆掉一个东西之前，先搞清楚它为什么在那里。但也要问：它还在吗？",
        intensity=3,
        tags=["删减", "抽象", "必要性"],
    ),
    Strategy(
        id="arch.adversarial",
        domain="architecture",
        name="对手思维",
        provocation=(
            "设计一个专门让你这套架构崩溃的攻击者：他会怎么注入数据、"
            "怎么制造并发冲突、怎么触发级联故障、怎么利用你的假设盲区？"
            "从攻击者视角重建防御，而不是从建设者视角打补丁。"
        ),
        thinking_frame="红队思维：最了解系统弱点的人不是建造者，是攻击者。先想怎么死，再想怎么活。",
        intensity=4,
        tags=["安全", "攻击", "韧性"],
    ),
    Strategy(
        id="arch.scale_extreme",
        domain="architecture",
        name="规模极端化",
        provocation=(
            "把你的数据量乘以 100000，或者除以 10000。"
            "你的设计在哪个极端下会彻底崩溃？崩溃的方式揭示了什么隐含假设？"
            "反过来：为极端规模设计的方案，在正常规模下有没有意外的好处？"
        ),
        thinking_frame="尺度思维：物理定律在不同尺度下表现不同。软件架构也是。",
        intensity=3,
        tags=["规模", "极端", "假设"],
    ),
    Strategy(
        id="arch.temporal_inversion",
        domain="architecture",
        name="时间反转",
        provocation=(
            "如果需求是倒着来的——先有输出结果，再反推输入；"
            "先有最终用户的行为数据，再决定功能；先有错误日志，再写代码。"
            "这种'逆向工程'式开发会让架构变成什么样？"
        ),
        thinking_frame="逆向思维：从终态倒推往往比从初态正推更能发现真正的需求。",
        intensity=4,
        tags=["时间", "逆向", "需求"],
    ),
    Strategy(
        id="arch.org_mirror",
        domain="architecture",
        name="组织映射",
        provocation=(
            "Conway 定律说系统结构镜像组织结构。反过来用：如果你故意让代码结构"
            "镜像一个完全不同的组织形式（军队、爵士乐队、开源社区、厨房brigade），"
            "模块划分和通信方式会怎么变？"
        ),
        thinking_frame="组织拓扑学：通信成本决定架构。改变通信模式就改变了架构。",
        intensity=2,
        tags=["组织", "Conway", "通信"],
    ),
    Strategy(
        id="arch.obsolescence",
        domain="architecture",
        name="假设过期",
        provocation=(
            "如果你架构中最核心的那个技术依赖（数据库/框架/协议/云服务）"
            "明天被宣布停止维护，你的系统怎么活？"
            "你现在有多少'隐性耦合'伪装成了'合理依赖'？"
        ),
        thinking_frame="反脆弱：真正的健壮不是'不会坏'，是'坏了能换'。你的可替换性有多高？",
        intensity=5,
        tags=["依赖", "反脆弱", "可替换"],
    ),
]
