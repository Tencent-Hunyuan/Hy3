from hy3_code_review_mcp.review import (
    ReviewRequest,
    build_review_prompt,
    review_patch_with_client,
    suggest_tests_with_client,
)


class FakeHy3Client:
    def __init__(self):
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "HY3 review result"


def test_build_review_prompt_includes_focus_and_patch():
    prompt = build_review_prompt(
        ReviewRequest(
            diff_text="+ risky_change()",
            focus="security",
            context="Python service",
        )
    )

    assert "security" in prompt
    assert "Python service" in prompt
    assert "+ risky_change()" in prompt
    assert "blocker" in prompt.lower()


def test_review_patch_with_client_calls_hy3_client():
    client = FakeHy3Client()

    result = review_patch_with_client(
        patch_text="+ risky_change()",
        client=client,
        language="python",
        focus="correctness",
    )

    assert result["review"] == "HY3 review result"
    assert result["metadata"]["language"] == "python"
    assert client.prompts and "+ risky_change()" in client.prompts[0]


def test_suggest_tests_with_client_calls_hy3_client():
    client = FakeHy3Client()

    result = suggest_tests_with_client(
        diff_text="+ add retry loop",
        client=client,
        test_framework="pytest",
        risk_level="high",
    )

    assert result["test_suggestions"] == "HY3 review result"
    assert "pytest" in client.prompts[0]
    assert "high" in client.prompts[0]
