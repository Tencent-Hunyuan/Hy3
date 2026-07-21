"""策略注册表与抽取逻辑。"""

from __future__ import annotations

import random

from .models import Strategy
from .ui import UI_STRATEGIES
from .architecture import ARCH_STRATEGIES
from .general import GENERAL_STRATEGIES


class StrategyRegistry:
    """策略注册表：存储、抽取、组合。"""

    def __init__(self):
        self._strategies: list[Strategy] = []
        self._register_all()

    def _register_all(self):
        self._strategies.extend(UI_STRATEGIES)
        self._strategies.extend(ARCH_STRATEGIES)
        self._strategies.extend(GENERAL_STRATEGIES)

    @property
    def all(self) -> list[Strategy]:
        return list(self._strategies)

    def select(
        self,
        domain: str,
        intensity: int,
        count: int = 2,
        exclude: list[str] | None = None,
    ) -> list[Strategy]:
        """根据领域和强度抽取策略组合。

        逻辑：
        1. 过滤 domain 匹配（general 策略对所有 domain 可用）
        2. 排除已用过的（avoid escalate 重复）
        3. 加权：intensity 越接近目标值权重越高
        4. 去重 tags：尽量选不同思维角度
        """
        exclude = set(exclude or [])

        # 候选池：domain 匹配 + general
        candidates = [
            s for s in self._strategies
            if s.id not in exclude
            and (s.domain == domain or s.domain == "general")
        ]

        if not candidates:
            candidates = [s for s in self._strategies if s.id not in exclude]

        # 加权：与目标 intensity 的距离越小权重越高
        def weight(s: Strategy) -> float:
            distance = abs(s.intensity - intensity)
            return max(0.1, 1.0 - distance * 0.25)

        # 按权重采样，同时尽量 tag 多样性
        selected: list[Strategy] = []
        used_tags: set[str] = set()
        pool = list(candidates)

        for _ in range(min(count, len(pool))):
            weights = []
            for s in pool:
                w = weight(s)
                # tag 多样性加成：如果 tag 都没用过，权重 ×1.5
                if not (set(s.tags) & used_tags):
                    w *= 1.5
                weights.append(w)

            total = sum(weights)
            r = random.uniform(0, total)
            cumulative = 0.0
            for i, s in enumerate(pool):
                cumulative += weights[i]
                if r <= cumulative:
                    selected.append(s)
                    used_tags.update(s.tags)
                    pool.pop(i)
                    break

        return selected

    def get_by_id(self, strategy_id: str) -> Strategy | None:
        for s in self._strategies:
            if s.id == strategy_id:
                return s
        return None
