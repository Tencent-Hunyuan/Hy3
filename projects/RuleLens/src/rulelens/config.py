"""配置读取。

从环境变量（以及可选的 .env 文件）读取 Hy3 与文档限制配置。
- 不在 import 阶段终止进程；
- 提供 `is_configured` 用于 UI 判断；
- `public_summary` / `masked_key` 不暴露真实密钥。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .exceptions import ConfigurationError

DEFAULTS = {
    "HY3_REASONING_EFFORT": "high",
    "HY3_ENABLE_REASONING_PARAM": "true",
    "HY3_REASONING_PARAM_STYLE": "chat_template_kwargs",
    "HY3_ENABLE_RESPONSE_FORMAT": "true",
    "HY3_TIMEOUT_SECONDS": "120",
    "HY3_MAX_RETRIES": "2",
    "RULELENS_MAX_FILE_MB": "10",
    "RULELENS_MAX_CHARS": "100000",
}

# 必须提供，否则 is_configured 为 False。
REQUIRED_KEYS = ("HY3_API_KEY", "HY3_BASE_URL", "HY3_MODEL")


@dataclass
class Settings:
    hy3_api_key: str
    hy3_base_url: str
    hy3_model: str
    hy3_reasoning_effort: str = "high"
    hy3_enable_reasoning_param: bool = True
    hy3_reasoning_param_style: str = "chat_template_kwargs"
    hy3_enable_response_format: bool = True
    hy3_timeout_seconds: int = 120
    hy3_max_retries: int = 2
    max_file_mb: int = 10
    max_chars: int = 100_000

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @property
    def is_configured(self) -> bool:
        return (
            bool(self.hy3_api_key)
            and self.hy3_api_key != "replace_me"
            and bool(self.hy3_base_url)
            and bool(self.hy3_model)
        )

    def masked_key(self) -> str:
        """返回脱敏后的密钥预览，用于 UI 展示连通状态。"""
        key = self.hy3_api_key
        if not key or key == "replace_me":
            return "（未配置）"
        if len(key) <= 6:
            return "*" * len(key)
        return f"{key[:3]}{'*' * (len(key) - 6)}{key[-3:]}"

    def public_summary(self) -> dict[str, str]:
        """不暴露密钥的公开配置摘要，供侧边栏展示。"""
        return {
            "base_url": self.hy3_base_url,
            "model": self.hy3_model,
            "reasoning_effort": self.hy3_reasoning_effort,
            "enable_reasoning_param": str(self.hy3_enable_reasoning_param),
            "reasoning_param_style": self.hy3_reasoning_param_style,
            "enable_response_format": str(self.hy3_enable_response_format),
            "timeout_seconds": str(self.hy3_timeout_seconds),
            "max_retries": str(self.hy3_max_retries),
            "max_file_mb": str(self.max_file_mb),
            "max_chars": str(self.max_chars),
            "api_key": self.masked_key(),
        }

    def validate_required(self) -> None:
        """在需要真实调用前检查必填项，缺失时抛出用户可读的 ConfigurationError。"""
        missing = [key for key in REQUIRED_KEYS if not getattr(self, _setting_attr(key))]
        if missing:
            raise ConfigurationError(
                user_message=(
                    "缺少必要的 Hy3 配置，请检查 .env 中的 "
                    "HY3_API_KEY、HY3_BASE_URL 与 HY3_MODEL 是否已填写。"
                )
            )


def _setting_attr(env_key: str) -> str:
    return {
        "HY3_API_KEY": "hy3_api_key",
        "HY3_BASE_URL": "hy3_base_url",
        "HY3_MODEL": "hy3_model",
    }[env_key]


def load_settings(*, env_file: str | None = None) -> Settings:
    """加载并合并环境变量。

    :param env_file: 可选 .env 路径；默认交给 python-dotenv 在 CWD 及上层目录中查找。
    """
    if env_file is not None:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    def get(key: str, default: str) -> str:
        return os.getenv(key, default)

    api_key = os.getenv("HY3_API_KEY", "")
    base_url = os.getenv("HY3_BASE_URL", "")
    model = os.getenv("HY3_MODEL", "")

    enable_reasoning = get(
        "HY3_ENABLE_REASONING_PARAM", DEFAULTS["HY3_ENABLE_REASONING_PARAM"]
    ).lower()
    enable_response_format = get(
        "HY3_ENABLE_RESPONSE_FORMAT", DEFAULTS["HY3_ENABLE_RESPONSE_FORMAT"]
    ).lower()
    reasoning_param_style = get(
        "HY3_REASONING_PARAM_STYLE", DEFAULTS["HY3_REASONING_PARAM_STYLE"]
    ).lower()
    if reasoning_param_style not in ("chat_template_kwargs", "direct"):
        reasoning_param_style = DEFAULTS["HY3_REASONING_PARAM_STYLE"]
    try:
        timeout = int(get("HY3_TIMEOUT_SECONDS", DEFAULTS["HY3_TIMEOUT_SECONDS"]))
    except ValueError:
        timeout = int(DEFAULTS["HY3_TIMEOUT_SECONDS"])
    try:
        retries = int(get("HY3_MAX_RETRIES", DEFAULTS["HY3_MAX_RETRIES"]))
    except ValueError:
        retries = int(DEFAULTS["HY3_MAX_RETRIES"])
    try:
        max_mb = int(get("RULELENS_MAX_FILE_MB", DEFAULTS["RULELENS_MAX_FILE_MB"]))
    except ValueError:
        max_mb = int(DEFAULTS["RULELENS_MAX_FILE_MB"])
    try:
        max_chars = int(get("RULELENS_MAX_CHARS", DEFAULTS["RULELENS_MAX_CHARS"]))
    except ValueError:
        max_chars = int(DEFAULTS["RULELENS_MAX_CHARS"])

    return Settings(
        hy3_api_key=api_key,
        hy3_base_url=base_url,
        hy3_model=model,
        hy3_reasoning_effort=get("HY3_REASONING_EFFORT", DEFAULTS["HY3_REASONING_EFFORT"]),
        hy3_enable_reasoning_param=enable_reasoning in ("1", "true", "yes", "on"),
        hy3_reasoning_param_style=reasoning_param_style,
        hy3_enable_response_format=enable_response_format in ("1", "true", "yes", "on"),
        hy3_timeout_seconds=max(1, timeout),
        hy3_max_retries=max(0, retries),
        max_file_mb=max(1, max_mb),
        max_chars=max(1, max_chars),
    )
