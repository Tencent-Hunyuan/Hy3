"""策略注册表与抽取逻辑。"""

from __future__ import annotations

import random
from collections import deque

from .models import Strategy
from .ui import UI_STRATEGIES
from .architecture import ARCH_STRATEGIES
from .general import GENERAL_STRATEGIES

# 跨调用去重：记住最近使用的策略 ID，避免连续调用抽到相同策略
_RECENT_SIZE = 6


class StrategyRegistry:
    """策略注册表：存储、抽取、组合。"""

    def __init__(self):
        self._strategies: list[Strategy] = []
        self._recent: deque[str] = deque(maxlen=_RECENT_SIZE)
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
        2. 排除已用过的（avoid escalate 重复）+ 排除近期使用过的（跨调用去重）
        3. 加权：intensity 越接近目标值权重越高
        4. 去重 tags：尽量选不同思维角度
        5. 如果过滤后候选不足，逐步放宽近期排除
        """
        exclude = set(exclude or [])

        # 候选池：domain 匹配 + general，排除显式 exclude 和近期使用
        recent_set = set(self._recent)
        candidates = [
            s for s in self._strategies
            if s.id not in exclude
            and s.id not in recent_set
            and (s.domain == domain or s.domain == "general")
        ]

        # 放宽策略：如果候选不足 count 条，只排除最近 3 条
        if len(candidates) < count:
            recent_relaxed = set(list(self._recent)[-3:])
            candidates = [
                s for s in self._strategies
                if s.id not in exclude
                and s.id not in recent_relaxed
                and (s.domain == domain or s.domain == "general")
            ]

        # 仍然不足则全量（仅排除显式 exclude）
        if not candidates:
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

        # 记录本次使用的策略 ID（跨调用去重）
        for s in selected:
            self._recent.append(s.id)

        return selected

    def get_by_id(self, strategy_id: str) -> Strategy | None:
        for s in self._strategies:
            if s.id == strategy_id:
                return s
        return None
