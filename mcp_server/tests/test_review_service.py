from pathlib import Path

import pytest

from hy3_code_review_mcp.git_service import GitService
from hy3_code_review_mcp.review_service import ReviewService


class FakeAnalyzer:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    async def analyze(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "reasoning_effort": reasoning_effort,
            }
        )
        return "mock analysis"


@pytest.mark.asyncio
async def test_service_builds_grounded_prompt(tmp_path: Path) -> None:
    analyzer = FakeAnalyzer()
    service = ReviewService(GitService(tmp_path, 10_000), analyzer)

    result = await service.run(
        task="review",
        source="provided",
        provided_diff="diff --git a/a.py b/a.py\n+print('hello')",
        focus="security",
        reasoning_effort="high",
    )

    assert result == "mock analysis"
    call = analyzer.calls[0]
    assert "<untrusted_diff>" in str(call["user_prompt"])
    assert "Review focus: security" in str(call["user_prompt"])
    assert "untrusted data" in str(call["system_prompt"])
    assert call["reasoning_effort"] == "high"


@pytest.mark.asyncio
async def test_test_prompt_does_not_lock_in_vulnerable_behavior(tmp_path: Path) -> None:
    analyzer = FakeAnalyzer()
    service = ReviewService(GitService(tmp_path, 10_000), analyzer)

    await service.run(
        task="tests",
        source="provided",
        provided_diff=(
            "diff --git a/users.py b/users.py\n"
            "+query = f\"SELECT * FROM users WHERE name = '{name}'\""
        ),
        test_framework="pytest",
        reasoning_effort="high",
    )

    prompt = str(analyzer.calls[0]["user_prompt"])
    assert "Never make vulnerable or broken behavior a passing regression requirement" in prompt
    assert "failing before the fix and passing after the fix" in prompt
    assert "assertions enforce the safe outcome" in prompt
    assert "Never propose a passing test that asserts an exploit succeeds" in prompt
    assert "Treat personal data such as email addresses" in prompt
    assert "raw value is absent or explicitly redacted" in prompt
    assert "never treat logging the raw personal value as correct normal behavior" in prompt
    assert "Test target: corrected implementation (secure-post-fix-v1)" in prompt
