"""测试共享配置。"""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """固定使用 asyncio 后端。"""
    return "asyncio"
