"""Deterministic OpenAPI checks that complement Hy3 semantic analysis."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from .models import Finding
from .spec_loader import HTTP_METHODS, LoadedSpec

_PATH_PARAMETER = re.compile(r"\{([^{}]+)\}")


def iter_operations(
    document: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any], list[Any]]]:
    """Yield path, method, operation, and combined path/operation parameters."""
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        shared_parameters = path_item.get("parameters", [])
        if not isinstance(shared_parameters, list):
            shared_parameters = []
        for method, operation in path_item.items():
            if str(method).lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            operation_parameters = operation.get("parameters", [])
            if not isinstance(operation_parameters, list):
                operation_parameters = []
            yield (
                str(path),
                str(method).lower(),
                operation,
                [*shared_parameters, *operation_parameters],
            )


def _finding(
    severity: str,
    category: str,
    location: str,
    message: str,
    suggestion: str,
) -> Finding:
    return Finding(
        severity=severity,  # type: ignore[arg-type]
        category=category,
        location=location,
        message=message,
        suggestion=suggestion,
    )


def audit_locally(spec: LoadedSpec) -> list[Finding]:
    """Run bounded, deterministic checks without executing external references."""
    document = spec.document
    findings: list[Finding] = []
    info = document.get("info", {})
    if isinstance(info, dict) and not str(info.get("description", "")).strip():
        findings.append(
            _finding(
                "low",
                "documentation",
                "info.description",
                "The API has no top-level description.",
                "Describe the API purpose, audience, authentication, and compatibility policy.",
            )
        )

    servers = document.get("servers")
    if not isinstance(servers, list) or not servers:
        findings.append(
            _finding(
                "low",
                "server",
                "servers",
                "No server URL is declared.",
                (
                    "Declare at least one environment-neutral server URL or document why it "
                    "is omitted."
                ),
            )
        )
    else:
        for index, server in enumerate(servers):
            if not isinstance(server, dict):
                continue
            url = str(server.get("url", ""))
            if url.startswith("http://") and not url.startswith(
                ("http://localhost", "http://127.0.0.1")
            ):
                findings.append(
                    _finding(
                        "high",
                        "transport_security",
                        f"servers[{index}].url",
                        "A non-local server uses plaintext HTTP.",
                        "Use HTTPS for credentials and API traffic.",
                    )
                )

    operation_ids: dict[str, str] = {}
    components = document.get("components", {})
    security_schemes = components.get("securitySchemes", {}) if isinstance(components, dict) else {}
    global_security = document.get("security")

    for path, method, operation, parameters in iter_operations(document):
        location = f"paths.{path}.{method}"
        operation_id = str(operation.get("operationId", "")).strip()
        if not operation_id:
            findings.append(
                _finding(
                    "medium",
                    "operation_id",
                    location,
                    "The operation has no operationId.",
                    "Add a stable, unique operationId for SDK generation and observability.",
                )
            )
        elif operation_id in operation_ids:
            findings.append(
                _finding(
                    "high",
                    "operation_id",
                    f"{location}.operationId",
                    f"operationId '{operation_id}' duplicates {operation_ids[operation_id]}.",
                    "Use a unique operationId for every operation.",
                )
            )
        else:
            operation_ids[operation_id] = location

        if (
            not str(operation.get("summary", "")).strip()
            and not str(operation.get("description", "")).strip()
        ):
            findings.append(
                _finding(
                    "low",
                    "documentation",
                    location,
                    "The operation has neither a summary nor a description.",
                    "Document its behavior, authorization, side effects, and important errors.",
                )
            )

        responses = operation.get("responses")
        if not isinstance(responses, dict) or not responses:
            findings.append(
                _finding(
                    "high",
                    "response_contract",
                    f"{location}.responses",
                    "The operation declares no responses.",
                    "Declare success and relevant error responses with schemas.",
                )
            )
        elif not any(str(code).startswith("2") for code in responses):
            findings.append(
                _finding(
                    "high",
                    "response_contract",
                    f"{location}.responses",
                    "The operation has no explicit 2xx success response.",
                    "Declare at least one successful response and its content schema.",
                )
            )

        declared_path_parameters = {
            str(parameter.get("name"))
            for parameter in parameters
            if isinstance(parameter, dict) and parameter.get("in") == "path"
        }
        placeholders = set(_PATH_PARAMETER.findall(path))
        for missing in sorted(placeholders - declared_path_parameters):
            findings.append(
                _finding(
                    "high",
                    "path_parameter",
                    location,
                    f"Path placeholder '{{{missing}}}' has no matching path parameter.",
                    "Declare it as an in:path parameter and set required:true.",
                )
            )
        for parameter in parameters:
            if (
                isinstance(parameter, dict)
                and parameter.get("in") == "path"
                and parameter.get("required") is not True
            ):
                findings.append(
                    _finding(
                        "medium",
                        "path_parameter",
                        f"{location}.parameters.{parameter.get('name', '?')}",
                        "An OpenAPI path parameter is not marked required.",
                        "Set required:true; path parameters are always required.",
                    )
                )

        effective_security = operation.get("security", global_security)
        if (
            method in {"post", "put", "patch", "delete"}
            and isinstance(security_schemes, dict)
            and security_schemes
            and not effective_security
        ):
            findings.append(
                _finding(
                    "medium",
                    "authorization",
                    f"{location}.security",
                    "A state-changing operation is explicitly or effectively unauthenticated.",
                    "Declare the intended security requirement or document why it is public.",
                )
            )

    return findings
