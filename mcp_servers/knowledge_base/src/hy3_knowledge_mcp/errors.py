"""知识库服务的领域异常。"""


class KnowledgeBaseError(Exception):
    """知识库服务的基础异常。"""


class ConfigurationError(KnowledgeBaseError):
    """配置无效或不完整。"""


class PathNotAllowedError(KnowledgeBaseError):
    """路径不在允许访问的根目录内。"""


class UnsupportedFileError(KnowledgeBaseError):
    """文件格式不受支持。"""


class LimitExceededError(KnowledgeBaseError):
    """操作超过已配置的资源限制。"""


class IndexNotFoundError(KnowledgeBaseError):
    """指定的知识库索引不存在。"""


class SourceNotFoundError(KnowledgeBaseError):
    """指定的知识来源不存在。"""


class FtsUnavailableError(KnowledgeBaseError):
    """全文检索能力不可用。"""


class Hy3AuthenticationError(KnowledgeBaseError):
    """Hy3 端点认证失败。"""


class Hy3RateLimitError(KnowledgeBaseError):
    """Hy3 端点触发速率限制。"""


class Hy3TimeoutError(KnowledgeBaseError):
    """Hy3 端点请求超时。"""


class Hy3ResponseError(KnowledgeBaseError):
    """Hy3 端点返回无效响应。"""


class CitationValidationError(KnowledgeBaseError):
    """回答中的引用无法通过验证。"""
