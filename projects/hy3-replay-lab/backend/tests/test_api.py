from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from replaylab.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_builtin_coding_loop_runs_through_the_local_http_api(monkeypatch) -> None:
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        health = await client.get("/api/health")
        fixtures = await client.get("/api/fixtures")
        analysis = await client.post(
            "/api/analyze",
            json={"fixture_id": "coding-loop", "provider": "fake"},
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "live_provider_configured": False}
    assert fixtures.status_code == 200
    assert {item["fixture_id"] for item in fixtures.json()} == {
        "coding-loop",
        "research-grounding",
    }
    assert analysis.status_code == 200
    payload = analysis.json()
    assert payload["report"]["finding"]["first_divergence_step_id"] == (
        "step-006-repeat-patch"
    )
    assert payload["exports"]["json"].startswith("{\n")
    assert "## 最小重放计划" in payload["exports"]["markdown"]


@pytest.mark.asyncio
async def test_live_analysis_without_a_key_fails_without_provider_details(monkeypatch) -> None:
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        response = await client.post(
            "/api/analyze",
            json={"fixture_id": "coding-loop", "provider": "hy3"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "尚未配置在线 Hy3"}


@pytest.mark.asyncio
async def test_invalid_live_configuration_is_reported_without_echoing_it(monkeypatch) -> None:
    secret = "CONFIGSECRET321"
    monkeypatch.setenv("HY3_API_KEY", "test-key")
    monkeypatch.setenv("HY3_BASE_URL", f"https://user:{secret}@hy3.test/v1")
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        response = await client.post(
            "/api/analyze",
            json={"fixture_id": "coding-loop", "provider": "hy3"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Hy3 分析请求失败"}
    assert secret not in response.text


@pytest.mark.asyncio
async def test_live_rate_limit_reaches_the_ui_with_only_retry_after(monkeypatch) -> None:
    from replaylab.hy3 import Hy3ProviderError

    class RateLimitedProvider:
        name = "fake-live"
        model = "hy3"
        mode = "live"

        def __init__(self, settings) -> None:
            del settings

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            del args

        async def analyze(self, task):
            del task
            raise Hy3ProviderError(
                "Hy3 request failed after retries (status 429)",
                status_code=429,
                retry_after_seconds=4,
            )

        async def repair(self, task, invalid_output, failure_code):
            del task, invalid_output, failure_code
            raise AssertionError("repair should not run")

    monkeypatch.setenv("HY3_API_KEY", "test-key")
    monkeypatch.setattr("replaylab.main.Hy3Provider", RateLimitedProvider)
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        response = await client.post(
            "/api/analyze", json={"fixture_id": "coding-loop", "provider": "hy3"}
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "4"
    assert response.json() == {"detail": "Hy3 当前请求受限"}


@pytest.mark.asyncio
async def test_imported_json_can_be_normalized_but_fake_analysis_is_refused() -> None:
    content = (PROJECT_ROOT / "fixtures" / "coding-loop" / "input.json").read_text(
        encoding="utf-8"
    )
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        imported = await client.post(
            "/api/import",
            json={
                "filename": "coding-loop.json",
                "content_type": "application/json",
                "content": content,
            },
        )
        analysis = await client.post(
            "/api/analyze",
            json={"task": imported.json(), "provider": "fake"},
        )

    assert imported.status_code == 200
    assert imported.json()["trace"][5]["step_id"] == "step-006-repeat-patch"
    assert analysis.status_code == 400
    assert analysis.json() == {"detail": "自定义导入需要使用在线 Hy3"}


@pytest.mark.asyncio
async def test_invalid_import_request_does_not_echo_private_input() -> None:
    private_input = "TOPSECRET123"
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        response = await client.post(
            "/api/import",
            json={
                "filename": "trace.json",
                "content_type": "application/json",
                "content": {"private_trace": private_input},
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "请求未通过校验"}
    assert private_input not in response.text


@pytest.mark.asyncio
async def test_invalid_analysis_request_does_not_echo_private_input() -> None:
    private_input = "ANOTHERSECRET456"
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        response = await client.post(
            "/api/analyze",
            json={"task": {"private_trace": private_input}, "provider": "hy3"},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "请求未通过校验"}
    assert private_input not in response.text


@pytest.mark.asyncio
async def test_normalized_custom_task_runs_through_the_live_provider_boundary(
    monkeypatch,
) -> None:
    import json

    output = json.loads(
        (PROJECT_ROOT / "fixtures" / "coding-loop" / "provider-output.json").read_text(
            encoding="utf-8"
        )
    )
    task = json.loads(
        (PROJECT_ROOT / "fixtures" / "coding-loop" / "input.json").read_text(
            encoding="utf-8"
        )
    )

    class SuccessfulLiveProvider:
        name = "test-live"
        model = "hy3"
        mode = "live"

        def __init__(self, settings) -> None:
            del settings

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            del args

        async def analyze(self, normalized_task):
            del normalized_task
            return output

        async def repair(self, normalized_task, invalid_output, failure_code):
            del normalized_task, invalid_output, failure_code
            return output

    monkeypatch.setenv("HY3_API_KEY", "test-key")
    monkeypatch.setattr("replaylab.main.Hy3Provider", SuccessfulLiveProvider)
    transport = ASGITransport(app=create_app(fixture_root=PROJECT_ROOT / "fixtures"))
    async with AsyncClient(transport=transport, base_url="http://replaylab.local") as client:
        response = await client.post(
            "/api/analyze", json={"task": task, "provider": "hy3"}
        )

    assert response.status_code == 200
    assert response.json()["report"]["metadata"]["mode"] == "live"
    assert response.json()["report"]["finding"]["first_divergence_step_id"] == (
        "step-006-repeat-patch"
    )
