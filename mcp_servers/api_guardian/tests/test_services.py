from __future__ import annotations

import pytest
from conftest import FakeHy3Client
from test_diff_engine import NEW, OLD
from test_spec_loader import VALID_SPEC

from hy3_api_guardian.errors import SpecInputError
from hy3_api_guardian.services import (
    audit_openapi_service,
    detect_breaking_changes_service,
    generate_contract_tests_service,
)
from hy3_api_guardian.settings import Settings


@pytest.mark.asyncio
async def test_audit_service_calls_hy3_and_returns_usage(settings: Settings) -> None:
    fake = FakeHy3Client("# Review\nGrounded result")
    result = await audit_openapi_service(
        spec_path=None,
        spec_text=VALID_SPEC,
        focus="all",
        settings=settings,
        client=fake,
    )
    assert result.tool == "audit_openapi"
    assert result.hy3_analysis.startswith("# Review")
    assert result.usage.total_tokens == 120
    assert len(fake.calls) == 1
    assert "UNTRUSTED_OPENAPI_DATA" in fake.calls[0][1]


@pytest.mark.asyncio
async def test_audit_service_redacts_secret_before_hy3(settings: Settings) -> None:
    fake = FakeHy3Client()
    secret = "super-secret-bearer-token"
    spec = VALID_SPEC.replace("description: ok", f"description: 'Bearer {secret}'")
    await audit_openapi_service(
        spec_path=None,
        spec_text=spec,
        focus="security",
        settings=settings,
        client=fake,
    )
    assert secret not in fake.calls[0][1]
    assert "[REDACTED]" in fake.calls[0][1]


@pytest.mark.asyncio
async def test_breaking_change_service_calls_hy3(settings: Settings) -> None:
    fake = FakeHy3Client("Migration plan")
    result = await detect_breaking_changes_service(
        old_spec_path=None,
        old_spec_text=OLD,
        new_spec_path=None,
        new_spec_text=NEW,
        include_compatible=False,
        settings=settings,
        client=fake,
    )
    assert result.breaking_count >= 1
    assert all(change.kind != "compatible" for change in result.changes)
    assert result.hy3_migration_analysis == "Migration plan"
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_contract_test_service_strips_code_fence(settings: Settings) -> None:
    fake = FakeHy3Client("```python\nimport pytest\n\ndef test_health():\n    assert True\n```")
    result = await generate_contract_tests_service(
        spec_path=None,
        spec_text=VALID_SPEC,
        framework="pytest",
        selected_paths=["GET /health"],
        settings=settings,
        client=fake,
    )
    assert result.generated_code.startswith("import pytest")
    assert result.selected_operations == ["GET /health"]
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_contract_test_service_rejects_unknown_selector(settings: Settings) -> None:
    with pytest.raises(SpecInputError, match="did not match"):
        await generate_contract_tests_service(
            spec_path=None,
            spec_text=VALID_SPEC,
            framework="pytest",
            selected_paths=["/missing"],
            settings=settings,
            client=FakeHy3Client(),
        )


@pytest.mark.asyncio
async def test_contract_test_service_rejects_partially_unknown_selectors(
    settings: Settings,
) -> None:
    with pytest.raises(SpecInputError, match="/missing"):
        await generate_contract_tests_service(
            spec_path=None,
            spec_text=VALID_SPEC,
            framework="pytest",
            selected_paths=["GET /health", "/missing"],
            settings=settings,
            client=FakeHy3Client(),
        )


@pytest.mark.asyncio
async def test_contract_test_service_accepts_case_insensitive_method_selector(
    settings: Settings,
) -> None:
    result = await generate_contract_tests_service(
        spec_path=None,
        spec_text=VALID_SPEC,
        framework="pytest",
        selected_paths=["get /health"],
        settings=settings,
        client=FakeHy3Client("def test_health():\n    assert True"),
    )
    assert result.selected_operations == ["GET /health"]


@pytest.mark.asyncio
async def test_contract_test_service_rejects_spec_without_operations(settings: Settings) -> None:
    with pytest.raises(SpecInputError, match="no operations"):
        await generate_contract_tests_service(
            spec_path=None,
            spec_text="openapi: 3.1.0\ninfo: {title: Empty, version: 1}\npaths: {}",
            framework="pytest",
            selected_paths=None,
            settings=settings,
            client=FakeHy3Client(),
        )


@pytest.mark.asyncio
async def test_contract_test_service_limits_operation_count(settings: Settings) -> None:
    paths = "\n".join(
        f"  /items/{index}:\n    get:\n      responses:\n        '200': {{description: ok}}"
        for index in range(21)
    )
    spec = f"openapi: 3.1.0\ninfo: {{title: Many, version: 1}}\npaths:\n{paths}\n"
    with pytest.raises(SpecInputError, match="more than 20"):
        await generate_contract_tests_service(
            spec_path=None,
            spec_text=spec,
            framework="pytest",
            selected_paths=None,
            settings=settings,
            client=FakeHy3Client(),
        )
