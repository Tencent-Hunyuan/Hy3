"""知识库 MCP 服务使用的严格数据模型。"""

from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    WithJsonSchema,
    model_validator,
)

COLLECTION_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
_HEX_PREFIX_PATTERN = r"^[0-9a-f]{12}$"


def _reject_evidence_id_normalization(value: object) -> object:
    """拒绝会被字符串规范化隐藏的证据 ID 输入。"""
    if isinstance(value, str) and (
        value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError("证据 ID 格式无效")
    return value


EvidenceId = Annotated[
    str,
    BeforeValidator(_reject_evidence_id_normalization),
    Field(pattern=r"^S[1-9][0-9]*$", max_length=16),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": r"^S[1-9][0-9]*$",
            "maxLength": 16,
        }
    ),
]


def _reject_source_path_controls(value: object) -> object:
    """在字符串规范化前拒绝来源路径控制字符。"""
    if isinstance(value, (str, PurePosixPath, PureWindowsPath)) and any(
        ord(character) < 32 or ord(character) == 127 for character in str(value)
    ):
        raise ValueError("来源路径不得包含控制字符")
    return value


def _safe_source_path(value: PurePosixPath) -> PurePosixPath:
    """验证来源路径为不含父级跳转的相对路径。"""
    if any(ord(character) < 32 or ord(character) == 127 for character in str(value)):
        raise ValueError("来源路径不得包含控制字符")
    windows_path = PureWindowsPath(str(value))
    if (
        value == PurePosixPath(".")
        or value.is_absolute()
        or ".." in value.parts
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or bool(windows_path.root)
        or ".." in windows_path.parts
    ):
        raise ValueError("来源路径必须是安全的相对路径")
    return value


SafeSourcePath = Annotated[
    PurePosixPath,
    BeforeValidator(_reject_source_path_controls),
    AfterValidator(_safe_source_path),
]


class StrictModel(BaseModel):
    """拒绝额外字段并在赋值时持续验证的数据模型。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ResponseFormat(str, Enum):
    """工具响应的序列化格式。"""

    MARKDOWN = "markdown"
    JSON = "json"


class ReasoningEffort(str, Enum):
    """模型推理强度。"""

    NONE = "none"
    LOW = "low"
    HIGH = "high"


class EndpointProfile(str, Enum):
    """兼容的模型端点类型。"""

    LOCAL = "local"
    OPENROUTER = "openrouter"
    GENERIC = "generic"


class SourceFormat(str, Enum):
    """可索引的来源格式。"""

    MARKDOWN = "markdown"
    TEXT = "text"
    RST = "rst"
    PDF = "pdf"


class IndexDocumentsRequest(StrictModel):
    """索引一个目录或文件的请求。"""

    collection: str = Field(pattern=COLLECTION_PATTERN)
    path: str = Field(min_length=1, max_length=4096)
    recursive: bool = True
    replace: bool = False
    include_globs: tuple[str, ...] = Field(default=(), max_length=20)


class SearchRequest(StrictModel):
    """检索知识库证据的请求。"""

    collection: str = Field(pattern=COLLECTION_PATTERN)
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=8, ge=1, le=20)
    offset: int = Field(default=0, ge=0)
    source_paths: tuple[SafeSourcePath, ...] = Field(default=(), max_length=20)
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


class AskRequest(StrictModel):
    """根据知识库证据生成回答的请求。"""

    collection: str = Field(pattern=COLLECTION_PATTERN)
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=8, ge=1, le=12)
    source_paths: tuple[SafeSourcePath, ...] = Field(default=(), max_length=20)
    reasoning_effort: ReasoningEffort | None = None
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


class SummarizeSourceRequest(StrictModel):
    """总结单个知识来源的请求。"""

    collection: str = Field(pattern=COLLECTION_PATTERN)
    source_path: SafeSourcePath
    focus: str | None = Field(default=None, max_length=2000)
    reasoning_effort: ReasoningEffort | None = None
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


class ListSourcesRequest(StrictModel):
    """列出知识库来源的请求。"""

    collection: str = Field(pattern=COLLECTION_PATTERN)
    query: str | None = Field(default=None, max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


class AllowedRoot(StrictModel):
    """允许访问的规范化根目录。"""

    root_id: str = Field(pattern=_HEX_PREFIX_PATTERN)
    path: Path = Field(exclude=True)


class ResolvedTarget(StrictModel):
    """已解析并归属到允许根目录的目标。"""

    absolute_path: Path = Field(exclude=True)
    root: AllowedRoot


class ResolvedSource(StrictModel):
    """已解析且可被索引的来源文件。"""

    absolute_path: Path = Field(exclude=True)
    root_path: Path = Field(exclude=True)
    root_id: str
    relative_path: PurePosixPath
    source_path: SafeSourcePath
    size_bytes: int = Field(ge=0)
    mtime_ns: int = Field(ge=0)
    device_id: int = Field(ge=0)
    file_id: int = Field(ge=0)


class ParsedBlock(StrictModel):
    """从来源文件解析出的连续文本块。"""

    text: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    hard_boundary_before: bool = False


class ParsedDocument(StrictModel):
    """完成解析的来源文档。"""

    source_format: SourceFormat
    blocks: tuple[ParsedBlock, ...]
    page_count: int | None = Field(default=None, ge=1)


class ChunkDraft(StrictModel):
    """等待写入索引的文本分块。"""

    model_config = ConfigDict(frozen=True)

    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    char_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_char_count(self) -> "ChunkDraft":
        """确保记录的字符数与实际文本一致。"""
        if self.char_count != len(self.text):
            raise ValueError("char_count 必须等于文本长度")
        return self


class SearchHit(StrictModel):
    """一条带定位信息的检索证据。"""

    evidence_id: EvidenceId
    source_path: SafeSourcePath
    page_number: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    score: float
    snippet: str


class SearchResult(StrictModel):
    """分页检索结果。"""

    query: str
    total: int = Field(ge=0)
    count: int = Field(ge=0)
    offset: int = Field(ge=0)
    has_more: bool
    next_offset: int | None = Field(default=None, ge=0)
    results: tuple[SearchHit, ...]


class Citation(StrictModel):
    """回答或总结中可验证的来源引用。"""

    evidence_id: EvidenceId
    source_path: SafeSourcePath
    page_number: int | None = Field(default=None, ge=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)


class AskResult(StrictModel):
    """经过引用验证的知识库回答。"""

    answer: str
    grounded: bool
    insufficient_evidence: bool
    citations: tuple[Citation, ...]
    warnings: tuple[str, ...] = ()


class Hy3AnswerPayload(StrictModel):
    """Hy3 回答端点返回的结构化载荷。"""

    answer: str = Field(min_length=1)
    used_evidence_ids: tuple[EvidenceId, ...]
    insufficient_evidence: bool


class Hy3SummaryPayload(StrictModel):
    """Hy3 总结端点返回的结构化载荷。"""

    summary: str = Field(min_length=1)
    used_evidence_ids: tuple[EvidenceId, ...]


class SummaryResult(StrictModel):
    """经过引用验证的来源总结。"""

    summary: str
    coverage: str
    used_evidence_ids: tuple[EvidenceId, ...]
    citations: tuple[Citation, ...]
    warnings: tuple[str, ...] = ()


class SourceInfo(StrictModel):
    """已索引来源的公开元数据。"""

    source_path: SafeSourcePath
    source_format: SourceFormat
    size_bytes: int = Field(ge=0)
    page_count: int | None = Field(default=None, ge=1)
    chunk_count: int = Field(ge=0)
    content_sha256_prefix: str = Field(pattern=_HEX_PREFIX_PATTERN)
    indexed_at: str


class ListSourcesResult(StrictModel):
    """分页来源列表。"""

    total: int = Field(ge=0)
    count: int = Field(ge=0)
    offset: int = Field(ge=0)
    has_more: bool
    next_offset: int | None = Field(default=None, ge=0)
    sources: tuple[SourceInfo, ...]


class StoredFingerprint(StrictModel):
    """用于增量索引判断的持久化文件指纹。"""

    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mtime_ns: int = Field(ge=0)
    size_bytes: int = Field(ge=0)


class PreparedSource(StrictModel):
    """已从单一字节快照完成解析与分块的来源。"""

    source: ResolvedSource
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_format: SourceFormat
    page_count: int | None = Field(default=None, ge=1)
    chunks: tuple[ChunkDraft, ...]


class IndexFileError(StrictModel):
    """单个来源的安全索引错误。"""

    source_path: SafeSourcePath
    reason: str = Field(min_length=1)


class IndexDocumentsResult(StrictModel):
    """一次索引请求的可审计统计结果。"""

    collection: str = Field(pattern=COLLECTION_PATTERN)
    discovered_sources: int = Field(ge=0)
    indexed_sources: int = Field(ge=0)
    updated_sources: int = Field(ge=0)
    unchanged_sources: int = Field(ge=0)
    skipped_sources: int = Field(ge=0)
    failed_sources: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    errors: tuple[IndexFileError, ...] = ()


class RetrievedChunk(StrictModel):
    """从本地索引读取的一条完整分块。"""

    chunk_id: int = Field(gt=0)
    source_path: SafeSourcePath
    text: str
    page_number: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    rank: float


class RetrievedPage(StrictModel):
    """本地检索的分页结果。"""

    total: int = Field(ge=0)
    items: tuple[RetrievedChunk, ...]
    has_more: bool
    next_offset: int | None = Field(default=None, ge=0)


class QueryPlan(StrictModel):
    """已规范化并限制规模的本地检索查询计划。"""

    normalized_query: str
    fts_query: str | None
    like_terms: tuple[str, ...]


class Evidence(StrictModel):
    """预算截断完成后分配稳定编号的完整证据。"""

    evidence_id: EvidenceId
    chunk_id: int = Field(gt=0)
    source_path: SafeSourcePath
    text: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
