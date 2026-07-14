"""RuleLens 自定义异常层级。

所有异常都继承自 :class:`RuleLensError`，UI 层将其映射为用户可读的中文提示。
实现层应确保日志中不记录 API 密钥、完整请求头或完整敏感文档。
"""

from __future__ import annotations


class RuleLensError(Exception):
    """所有 RuleLens 错误的基类。"""

    # 用于在 UI 中展示的友好中文提示（子类可覆盖）。
    user_message: str = "发生了未知错误，请稍后重试或联系维护者。"

    def __init__(self, message: str = "", *, user_message: str | None = None) -> None:
        super().__init__(message or self.user_message)
        if user_message is not None:
            self.user_message = user_message


class ConfigurationError(RuleLensError):
    user_message = "系统配置不完整，请检查 .env 中的 HY3_BASE_URL 与 HY3_API_KEY。"


class UnsupportedFileError(RuleLensError):
    user_message = "不支持的文件类型，请上传 PDF、Markdown 或 TXT 文件。"


class FileTooLargeError(RuleLensError):
    user_message = "文件超过大小上限，请上传不超过限制的文件。"


class EmptyDocumentError(RuleLensError):
    user_message = "文档内容为空或无法提取文本，请检查文件后重试。"


class DocumentExtractionError(RuleLensError):
    user_message = "文档解析失败，当前版本不支持扫描版（无文本层）PDF，请转换为 TXT/MD。"


class Hy3AuthenticationError(RuleLensError):
    user_message = "Hy3 鉴权失败，请检查 .env 中的 HY3_API_KEY 是否正确。"


class Hy3RateLimitError(RuleLensError):
    user_message = "Hy3 接口限流，请稍后重试；如频繁出现，请检查服务配额。"


class Hy3TimeoutError(RuleLensError):
    user_message = "Hy3 响应超时，请稍后重试或调大 HY3_TIMEOUT_SECONDS。"


class Hy3ResponseError(RuleLensError):
    user_message = "Hy3 返回了异常响应，请稍后重试。"


class SchemaValidationError(RuleLensError):
    user_message = "模型输出格式异常，可重试。"
