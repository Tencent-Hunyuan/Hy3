"""策略库模块。"""

from .models import Strategy
from .registry import StrategyRegistry

registry = StrategyRegistry()
