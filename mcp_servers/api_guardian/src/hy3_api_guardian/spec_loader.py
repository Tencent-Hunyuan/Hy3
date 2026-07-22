"""Safe OpenAPI file/text loading and compact model projection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from yaml.events import AliasEvent

from .errors import SpecInputError
from .redaction import redact_structure, redact_text
from .settings import Settings

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}
MAX_CONTAINER_NODES = 200_000
MAX_NESTING_DEPTH = 100
MAX_LOCAL_REF_DEPTH = 16


class _NoAliasSafeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects aliases to avoid recursive or expansive graphs."""

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(AliasEvent):
            raise SpecInputError("YAML aliases are not supported in OpenAPI input")
        return super().compose_node(parent, index)


@dataclass(frozen=True, slots=True)
class LoadedSpec:
    """Validated source metadata and parsed OpenAPI document."""

    label: str
    document: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.document.get("openapi", "unknown"))

    @property
    def title(self) -> str:
        info = self.document.get("info")
        if isinstance(info, dict):
            return str(info.get("title", self.label))
        return self.label

    @property
    def operation_count(self) -> int:
        paths = self.document.get("paths", {})
        if not isinstance(paths, dict):
            return 0
        return sum(
            1
            for path_item in paths.values()
            if isinstance(path_item, dict)
            for method in path_item
            if str(method).lower() in HTTP_METHODS
        )


def _resolve_safe_path(raw_path: str, settings: Settings) -> Path:
    if not raw_path.strip():
        raise SpecInputError("spec_path cannot be empty")
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = settings.allowed_root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SpecInputError("The OpenAPI file does not exist or cannot be read") from exc
    if not resolved.is_relative_to(settings.allowed_root):
        raise SpecInputError("The OpenAPI file is outside HY3_ALLOWED_ROOT")
    if not resolved.is_file():
        raise SpecInputError("spec_path must point to a file")
    if resolved.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise SpecInputError("Only .json, .yaml, and .yml OpenAPI files are supported")
    if resolved.stat().st_size > settings.max_file_bytes:
        raise SpecInputError(
            f"The OpenAPI file exceeds HY3_MAX_FILE_BYTES ({settings.max_file_bytes} bytes)"
        )
    return resolved


def _parse_document(text: str, label: str) -> dict[str, Any]:
    try:
        value = (
            json.loads(text)
            if label.lower().endswith(".json")
            else yaml.load(text, Loader=_NoAliasSafeLoader)
        )
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise SpecInputError("The OpenAPI input is not valid JSON or YAML") from exc
    if not isinstance(value, dict):
        raise SpecInputError("The OpenAPI document root must be an object")
    _validate_document_shape(value)
    version = value.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        raise SpecInputError("Only OpenAPI 3.x documents are supported")
    if not isinstance(value.get("info"), dict):
        raise SpecInputError("The OpenAPI document must contain an info object")
    if not isinstance(value.get("paths"), dict):
        raise SpecInputError("The OpenAPI document must contain a paths object")
    return value


def _validate_document_shape(document: dict[str, Any]) -> None:
    """Bound nesting and collection count before projection or recursive redaction."""
    stack: list[tuple[Any, int]] = [(document, 0)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        if depth > MAX_NESTING_DEPTH:
            raise SpecInputError(
                f"The OpenAPI document exceeds the maximum nesting depth ({MAX_NESTING_DEPTH})"
            )
        if isinstance(value, dict):
            nodes += len(value)
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            nodes += len(value)
            stack.extend((item, depth + 1) for item in value)
        if nodes > MAX_CONTAINER_NODES:
            raise SpecInputError("The OpenAPI document contains too many fields")


def load_spec(
    *,
    spec_path: str | None,
    spec_text: str | None,
    settings: Settings,
    label: str = "inline-openapi.yaml",
) -> LoadedSpec:
    """Load exactly one file or inline OpenAPI source."""
    has_path = bool(spec_path and spec_path.strip())
    has_text = bool(spec_text and spec_text.strip())
    if has_path == has_text:
        raise SpecInputError("Provide exactly one of spec_path or spec_text")
    if has_path:
        resolved = _resolve_safe_path(spec_path or "", settings)
        try:
            text = resolved.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise SpecInputError("The OpenAPI file must be readable UTF-8 text") from exc
        document = _parse_document(text, resolved.name)
        return LoadedSpec(label=str(resolved), document=document)

    text = spec_text or ""
    if len(text.encode("utf-8")) > settings.max_file_bytes:
        raise SpecInputError(
            f"The inline OpenAPI input exceeds HY3_MAX_FILE_BYTES ({settings.max_file_bytes} bytes)"
        )
    return LoadedSpec(label=label, document=_parse_document(text, label))


def resolve_local_object(
    document: dict[str, Any], value: Any, *, max_depth: int = MAX_LOCAL_REF_DEPTH
) -> dict[str, Any] | None:
    """Resolve a bounded chain of local JSON Pointer references without network access."""
    current = value
    seen: set[str] = set()
    for _ in range(max_depth + 1):
        if not isinstance(current, dict):
            return None
        ref = current.get("$ref")
        if ref is None:
            return current
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            return None
        seen.add(ref)
        target: Any = document
        for raw_token in ref[2:].split("/"):
            token = raw_token.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or token not in target:
                return None
            target = target[token]
        current = target
    return None


def compact_for_model(spec: LoadedSpec, max_chars: int) -> str:
    """Project an OpenAPI document into a bounded, secret-reduced JSON representation."""
    document = spec.document
    compact: dict[str, Any] = {
        "openapi": document.get("openapi"),
        "info": document.get("info"),
        "security": document.get("security"),
        "paths": {},
        "components": {},
    }

    paths = document.get("paths", {})
    if isinstance(paths, dict):
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            projected_item: dict[str, Any] = {}
            if isinstance(path_item.get("parameters"), list):
                projected_item["parameters"] = path_item["parameters"]
            for method, operation in path_item.items():
                if str(method).lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                projected_item[str(method).lower()] = {
                    key: operation.get(key)
                    for key in (
                        "operationId",
                        "summary",
                        "description",
                        "parameters",
                        "requestBody",
                        "responses",
                        "security",
                        "deprecated",
                    )
                    if key in operation
                }
            compact["paths"][str(path)] = projected_item

    components = document.get("components", {})
    if isinstance(components, dict):
        for section in (
            "schemas",
            "parameters",
            "requestBodies",
            "responses",
            "headers",
            "securitySchemes",
        ):
            section_value = components.get(section)
            if isinstance(section_value, dict):
                compact["components"][section] = section_value

    serialized = json.dumps(redact_structure(compact), ensure_ascii=False, separators=(",", ":"))
    serialized = redact_text(serialized)
    if len(serialized) > max_chars:
        serialized = serialized[:max_chars] + "\n[TRUNCATED BY HY3_API_GUARDIAN]"
    return serialized
