from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from .git_utils import get_git_diff


class CompletionClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


@dataclass(frozen=True)
class ReviewRequest:
    diff_text: str
    focus: str = "correctness, security, reliability, and tests"
    context: str = ""


def build_review_prompt(request: ReviewRequest) -> str:
    context = request.context.strip() or "No extra context was provided."
    return f"""Review the following code change.

Focus areas: {request.focus}
Project context: {context}

Return concise markdown with these sections:
1. Summary
2. Findings ordered by severity: blocker, major, minor, nit
3. Missing or weak tests
4. Concrete fix suggestions

For each finding, include the impacted file/function when inferable and explain why it matters.

Diff:
```diff
{request.diff_text}
```
"""


def build_test_prompt(diff_text: str, test_framework: str, risk_level: str) -> str:
    return f"""Suggest tests for this code change.

Preferred test framework: {test_framework}
Risk level: {risk_level}

Return markdown with:
1. Highest-risk behavior to verify
2. Unit tests
3. Integration or regression tests
4. Edge cases and failure modes
5. Example test names

Diff:
```diff
{diff_text}
```
"""


def review_patch_with_client(
    patch_text: str,
    client: CompletionClient,
    language: str = "unknown",
    focus: str = "correctness, security, reliability, and tests",
    context: str = "",
) -> Dict[str, Any]:
    prompt = build_review_prompt(
        ReviewRequest(
            diff_text=patch_text,
            focus=focus,
            context=f"Language: {language}. {context}".strip(),
        )
    )
    return {
        "review": client.complete(prompt),
        "metadata": {
            "language": language,
            "focus": focus,
            "diff_chars": len(patch_text),
        },
    }


def review_git_diff_with_client(
    repo_path: str,
    client: CompletionClient,
    base_ref: str = "HEAD",
    target_ref: str | None = None,
    focus: str = "correctness, security, reliability, and tests",
    max_chars: int = 24000,
) -> Dict[str, Any]:
    diff = get_git_diff(
        repo_path=repo_path,
        base_ref=base_ref,
        target_ref=target_ref,
        max_chars=max_chars,
    )
    result = review_patch_with_client(
        patch_text=diff,
        client=client,
        language="diff",
        focus=focus,
        context=f"Repository: {repo_path}. Base ref: {base_ref}. Target ref: {target_ref or 'worktree'}.",
    )
    result["metadata"].update(
        {
            "repo_path": repo_path,
            "base_ref": base_ref,
            "target_ref": target_ref,
            "max_chars": max_chars,
        }
    )
    return result


def suggest_tests_with_client(
    diff_text: str,
    client: CompletionClient,
    test_framework: str = "pytest",
    risk_level: str = "medium",
) -> Dict[str, Any]:
    prompt = build_test_prompt(
        diff_text=diff_text,
        test_framework=test_framework,
        risk_level=risk_level,
    )
    return {
        "test_suggestions": client.complete(prompt),
        "metadata": {
            "test_framework": test_framework,
            "risk_level": risk_level,
            "diff_chars": len(diff_text),
        },
    }
