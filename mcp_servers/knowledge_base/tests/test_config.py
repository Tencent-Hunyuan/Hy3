"""知识库 MCP 配置测试。"""

import os
import traceback
from pathlib import Path

import pytest

from hy3_knowledge_mcp.config import Settings, max_structured_schema_chars
from hy3_knowledge_mcp.errors import ConfigurationError
from hy3_knowledge_mcp.models import EndpointProfile, ReasoningEffort


def _minimal_values(root: Path, storage: Path) -> dict[str, object]:
    """返回直接构造设置所需的最小字段。"""
    return {
        "allowed_root_paths": (root,),
        "storage_dir": storage,
    }


def test_from_env_requires_allowed_roots() -> None:
    with pytest.raises(ConfigurationError, match="HY3_KB_ROOTS"):
        Settings.from_env({})


def test_from_env_parses_explicit_values_and_resolves_paths(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    storage = tmp_path / "storage"
    first_root.mkdir()
    second_root.mkdir()

    settings = Settings.from_env(
        {
            "HY3_KB_ROOTS": os.pathsep.join((str(first_root), str(second_root))),
            "HY3_KB_STORAGE_DIR": str(storage),
            "HY3_BASE_URL": "http://localhost:8000/v1",
            "HY3_ENDPOINT_PROFILE": "local",
            "HY3_REASONING_EFFORT": "low",
            "HY3_TIMEOUT_SECONDS": "45",
            "HY3_MAX_RETRIES": "3",
            "HY3_MAX_OUTPUT_TOKENS": "1024",
            "HY3_KB_CHUNK_CHARS": "1200",
            "HY3_KB_CHUNK_OVERLAP_CHARS": "120",
            "HY3_KB_MAX_DISCOVERY_ENTRIES": "1000",
            "HY3_KB_MAX_DISCOVERY_DIRECTORIES": "100",
            "HY3_KB_MAX_DISCOVERY_DEPTH": "16",
            "HY3_KB_MAX_TOTAL_BYTES_PER_RUN": "123456",
            "HY3_KB_PROMPT_RESERVE_CHARS": "5000",
            "HY3_KB_MAX_SUMMARY_REQUESTS": "12",
        }
    )

    assert settings.allowed_root_paths == (first_root.resolve(), second_root.resolve())
    assert settings.storage_dir == storage.resolve()
    assert settings.api_key is None
    assert settings.endpoint_profile is EndpointProfile.LOCAL
    assert settings.reasoning_effort is ReasoningEffort.LOW
    assert settings.timeout_seconds == 45
    assert settings.max_retries == 3
    assert settings.max_output_tokens == 1024
    assert settings.chunk_chars == 1200
    assert settings.chunk_overlap_chars == 120
    assert settings.max_discovery_entries == 1000
    assert settings.max_discovery_directories == 100
    assert settings.max_discovery_depth == 16
    assert settings.max_total_bytes_per_run == 123456
    assert settings.prompt_reserve_chars == 5000
    assert settings.max_summary_requests == 12


def test_api_key_is_secret_in_representations(tmp_path: Path) -> None:
    secret = "super-secret-token"
    root = tmp_path / "root"
    root.mkdir()

    settings = Settings.from_env(
        {
            "HY3_KB_ROOTS": str(root),
            "HY3_API_KEY": secret,
        }
    )

    assert secret not in repr(settings)
    assert secret not in repr(settings.api_key)
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == secret


def test_path_error_does_not_expose_paths_or_exception_context(tmp_path: Path) -> None:
    secret = "super-secret-value"
    missing_root = tmp_path / "private-looking" / "knowledge-root"

    with pytest.raises(ConfigurationError) as exc_info:
        Settings.from_env(
            {
                "HY3_KB_ROOTS": str(missing_root),
                "HY3_API_KEY": secret,
            }
        )

    error = exc_info.value
    formatted = "".join(traceback.format_exception(error))
    for sensitive_value in (secret, str(missing_root), str(tmp_path)):
        assert sensitive_value not in str(error)
        assert sensitive_value not in repr(error)
        assert sensitive_value not in formatted
    assert error.__cause__ is None
    assert error.__context__ is None


def test_local_profile_rejects_non_loopback_endpoint(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(ConfigurationError, match="loopback"):
        Settings.from_env(
            {
                "HY3_KB_ROOTS": str(root),
                "HY3_BASE_URL": "https://remote.example/v1",
                "HY3_ENDPOINT_PROFILE": "local",
            }
        )


@pytest.mark.parametrize(
    ("profile", "base_url"),
    [
        ("local", "ftp://localhost/v1"),
        ("local", "http://user:embedded-secret@localhost:99999/v1"),
        ("generic", "not-a-url"),
        ("openrouter", "file:///tmp/socket"),
    ],
)
def test_from_env_rejects_invalid_base_urls(
    tmp_path: Path,
    profile: str,
    base_url: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(ConfigurationError, match="base_url"):
        Settings.from_env(
            {
                "HY3_KB_ROOTS": str(root),
                "HY3_ENDPOINT_PROFILE": profile,
                "HY3_BASE_URL": base_url,
            }
        )


def test_invalid_base_url_credentials_are_not_exposed(tmp_path: Path) -> None:
    credential = "embedded-secret"
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(ConfigurationError) as exc_info:
        Settings.from_env(
            {
                "HY3_KB_ROOTS": str(root),
                "HY3_ENDPOINT_PROFILE": "local",
                "HY3_BASE_URL": f"http://user:{credential}@localhost:99999/v1",
            }
        )

    error = exc_info.value
    formatted = "".join(traceback.format_exception(error))
    assert credential not in str(error)
    assert credential not in repr(error)
    assert credential not in formatted
    assert error.__cause__ is None
    assert error.__context__ is None


def test_validation_error_does_not_expose_api_key_in_exception_chain(tmp_path: Path) -> None:
    secret = "super-secret-value"
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(ConfigurationError) as exc_info:
        Settings.from_env(
            {
                "HY3_KB_ROOTS": str(root),
                "HY3_API_KEY": secret,
                "HY3_ENDPOINT_PROFILE": "local",
                "HY3_BASE_URL": "https://remote.example/v1",
            }
        )

    error = exc_info.value
    formatted = "".join(traceback.format_exception(error))
    assert secret not in str(error)
    assert secret not in repr(error)
    assert secret not in formatted
    assert error.__cause__ is None
    assert error.__context__ is None


def test_from_env_rejects_root_that_is_a_file(tmp_path: Path) -> None:
    root_file = tmp_path / "knowledge.txt"
    root_file.write_text("知识", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="路径"):
        Settings.from_env({"HY3_KB_ROOTS": str(root_file)})


def test_from_env_rejects_storage_below_existing_file_ancestor(tmp_path: Path) -> None:
    root = tmp_path / "root"
    storage_file = tmp_path / "storage-file"
    root.mkdir()
    storage_file.write_text("不是目录", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="路径"):
        Settings.from_env(
            {
                "HY3_KB_ROOTS": str(root),
                "HY3_KB_STORAGE_DIR": str(storage_file / "child-storage"),
            }
        )


def test_from_env_deduplicates_resolved_roots_in_first_seen_order(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()

    settings = Settings.from_env(
        {
            "HY3_KB_ROOTS": os.pathsep.join(
                (str(first_root), str(first_root / "."), str(second_root), str(first_root))
            )
        }
    )

    assert settings.allowed_root_paths == (first_root.resolve(), second_root.resolve())


def test_supplied_mapping_does_not_consult_dotenv_or_ambient_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("HY3_KB_ROOTS", str(tmp_path / "ambient-private-root"))

    def fail_if_dotenv_is_loaded(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"不应加载 dotenv: {args!r} {kwargs!r}")

    monkeypatch.setattr("hy3_knowledge_mcp.config.load_dotenv", fail_if_dotenv_is_loaded)

    settings = Settings.from_env({"HY3_KB_ROOTS": str(root)})

    assert settings.allowed_root_paths == (root.resolve(),)


def test_context_budget_accepts_exact_boundary_and_rejects_one_less(tmp_path: Path) -> None:
    root = tmp_path / "root"
    storage = tmp_path / "storage"
    root.mkdir()
    required = 3000 + max_structured_schema_chars() + 8000 + (2048 * 8)
    values = _minimal_values(root, storage)

    with pytest.raises(ValueError, match="output budget"):
        Settings.model_validate({**values, "max_context_chars": required - 1})

    settings = Settings.model_validate({**values, "max_context_chars": required})

    assert settings.max_context_chars == required


def test_chunk_overlap_accepts_half_and_rejects_more_than_half(tmp_path: Path) -> None:
    """生产配置保证每个普通窗口至少前进一半。"""
    values = _minimal_values(tmp_path / "root", tmp_path / "storage")

    settings = Settings.model_validate({**values, "chunk_chars": 1000, "chunk_overlap_chars": 500})

    assert settings.chunk_overlap_chars == 500
    with pytest.raises(ValueError, match="一半"):
        Settings.model_validate({**values, "chunk_chars": 1000, "chunk_overlap_chars": 501})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("HY3_TIMEOUT_SECONDS", "4"),
        ("HY3_MAX_RETRIES", "6"),
        ("HY3_MAX_OUTPUT_TOKENS", "0"),
        ("HY3_KB_CHUNK_CHARS", "100"),
        ("HY3_KB_CHUNK_OVERLAP_CHARS", "3000"),
        ("HY3_KB_MAX_DISCOVERY_DEPTH", "0"),
        ("HY3_KB_MAX_SUMMARY_REQUESTS", "1"),
    ],
)
def test_from_env_rejects_invalid_limits(tmp_path: Path, name: str, value: str) -> None:
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(ConfigurationError):
        Settings.from_env({"HY3_KB_ROOTS": str(root), name: value})
