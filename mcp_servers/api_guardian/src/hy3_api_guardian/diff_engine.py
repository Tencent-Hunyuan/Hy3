"""Deterministic OpenAPI compatibility comparison."""

from __future__ import annotations

from typing import Any

from .audit import iter_operations
from .models import ApiChange
from .spec_loader import LoadedSpec, resolve_local_object


def _change(kind: str, category: str, location: str, message: str) -> ApiChange:
    return ApiChange(kind=kind, category=category, location=location, message=message)  # type: ignore[arg-type]


def _operations(
    document: dict[str, Any],
) -> dict[tuple[str, str], tuple[dict[str, Any], list[Any]]]:
    return {
        (path, method): (operation, parameters)
        for path, method, operation, parameters in iter_operations(document)
    }


def _parameter_map(parameters: list[Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for parameter in parameters:
        if not isinstance(parameter, dict) or "$ref" in parameter:
            continue
        name = parameter.get("name")
        location = parameter.get("in")
        if isinstance(name, str) and isinstance(location, str):
            result[(location, name)] = parameter
    return result


def _schema_signature(parameter: dict[str, Any]) -> tuple[Any, Any, tuple[Any, ...]]:
    schema = parameter.get("schema", {})
    if not isinstance(schema, dict):
        return None, None, ()
    enum = schema.get("enum")
    enum_values = tuple(enum) if isinstance(enum, list) else ()
    return schema.get("type"), schema.get("format"), enum_values


def _security_required(operation: dict[str, Any], document: dict[str, Any]) -> bool:
    security = operation.get("security", document.get("security"))
    return isinstance(security, list) and bool(security)


def _compare_operations(old: LoadedSpec, new: LoadedSpec) -> list[ApiChange]:
    changes: list[ApiChange] = []
    old_operations = _operations(old.document)
    new_operations = _operations(new.document)

    for path, method in sorted(old_operations.keys() - new_operations.keys()):
        changes.append(
            _change(
                "breaking",
                "operation_removed",
                f"{method.upper()} {path}",
                "The operation was removed.",
            )
        )
    for path, method in sorted(new_operations.keys() - old_operations.keys()):
        changes.append(
            _change(
                "compatible",
                "operation_added",
                f"{method.upper()} {path}",
                "A new operation was added.",
            )
        )

    for key in sorted(old_operations.keys() & new_operations.keys()):
        path, method = key
        location = f"{method.upper()} {path}"
        old_operation, old_parameters = old_operations[key]
        new_operation, new_parameters = new_operations[key]

        old_params = _parameter_map(old_parameters)
        new_params = _parameter_map(new_parameters)
        for param_key in sorted(old_params.keys() - new_params.keys()):
            changes.append(
                _change(
                    "warning",
                    "parameter_removed",
                    f"{location} {param_key[0]}:{param_key[1]}",
                    "A request parameter was removed; generated clients may change.",
                )
            )
        for param_key in sorted(new_params.keys() - old_params.keys()):
            parameter = new_params[param_key]
            kind = "breaking" if parameter.get("required") is True else "compatible"
            changes.append(
                _change(
                    kind,
                    "parameter_added",
                    f"{location} {param_key[0]}:{param_key[1]}",
                    "A required request parameter was added."
                    if kind == "breaking"
                    else "An optional request parameter was added.",
                )
            )
        for param_key in sorted(old_params.keys() & new_params.keys()):
            old_parameter = old_params[param_key]
            new_parameter = new_params[param_key]
            param_location = f"{location} {param_key[0]}:{param_key[1]}"
            if old_parameter.get("required") is not True and new_parameter.get("required") is True:
                changes.append(
                    _change(
                        "breaking",
                        "parameter_required",
                        param_location,
                        "An existing optional parameter became required.",
                    )
                )
            old_type, old_format, old_enum = _schema_signature(old_parameter)
            new_type, new_format, new_enum = _schema_signature(new_parameter)
            if (old_type, old_format) != (new_type, new_format):
                changes.append(
                    _change(
                        "breaking",
                        "parameter_type",
                        param_location,
                        f"Parameter schema changed from {old_type}/{old_format} "
                        f"to {new_type}/{new_format}.",
                    )
                )
            removed_enum = set(old_enum) - set(new_enum)
            if removed_enum:
                changes.append(
                    _change(
                        "breaking",
                        "parameter_enum",
                        param_location,
                        f"Allowed enum values were removed: {sorted(map(str, removed_enum))}.",
                    )
                )

        old_body = resolve_local_object(old.document, old_operation.get("requestBody", {})) or {}
        new_body = resolve_local_object(new.document, new_operation.get("requestBody", {})) or {}
        if old_body.get("required") is not True and new_body.get("required") is True:
            changes.append(
                _change(
                    "breaking",
                    "request_body_required",
                    location,
                    "The request body became required.",
                )
            )

        old_responses = old_operation.get("responses", {})
        new_responses = new_operation.get("responses", {})
        if isinstance(old_responses, dict) and isinstance(new_responses, dict):
            for response_code in sorted(old_responses.keys() - new_responses.keys()):
                kind = "breaking" if str(response_code).startswith("2") else "warning"
                changes.append(
                    _change(
                        kind,
                        "response_removed",
                        f"{location} response:{response_code}",
                        "A documented response was removed.",
                    )
                )

        if not _security_required(old_operation, old.document) and _security_required(
            new_operation, new.document
        ):
            changes.append(
                _change(
                    "breaking",
                    "authentication_required",
                    location,
                    "The operation now requires authentication.",
                )
            )
    return changes


def _compare_component_schemas(old: LoadedSpec, new: LoadedSpec) -> list[ApiChange]:
    changes: list[ApiChange] = []
    old_components = old.document.get("components", {})
    new_components = new.document.get("components", {})
    old_schemas = old_components.get("schemas", {}) if isinstance(old_components, dict) else {}
    new_schemas = new_components.get("schemas", {}) if isinstance(new_components, dict) else {}
    if not isinstance(old_schemas, dict) or not isinstance(new_schemas, dict):
        return changes

    for schema_name in sorted(old_schemas.keys() - new_schemas.keys()):
        changes.append(
            _change(
                "breaking",
                "schema_removed",
                f"components.schemas.{schema_name}",
                "A reusable schema was removed.",
            )
        )
    for schema_name in sorted(old_schemas.keys() & new_schemas.keys()):
        old_schema = old_schemas[schema_name]
        new_schema = new_schemas[schema_name]
        if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
            continue
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        for property_name in sorted(new_required - old_required):
            changes.append(
                _change(
                    "breaking",
                    "required_property_added",
                    f"components.schemas.{schema_name}.{property_name}",
                    "A schema property became required.",
                )
            )
        old_properties = old_schema.get("properties", {})
        new_properties = new_schema.get("properties", {})
        if not isinstance(old_properties, dict) or not isinstance(new_properties, dict):
            continue
        for property_name in sorted(old_properties.keys() - new_properties.keys()):
            changes.append(
                _change(
                    "warning",
                    "schema_property_removed",
                    f"components.schemas.{schema_name}.{property_name}",
                    "A schema property was removed.",
                )
            )
        for property_name in sorted(old_properties.keys() & new_properties.keys()):
            old_property = old_properties[property_name]
            new_property = new_properties[property_name]
            if not isinstance(old_property, dict) or not isinstance(new_property, dict):
                continue
            old_signature = (old_property.get("type"), old_property.get("format"))
            new_signature = (new_property.get("type"), new_property.get("format"))
            if old_signature != new_signature:
                changes.append(
                    _change(
                        "breaking",
                        "schema_property_type",
                        f"components.schemas.{schema_name}.{property_name}",
                        f"Property schema changed from {old_signature} to {new_signature}.",
                    )
                )
    return changes


def compare_specs(old: LoadedSpec, new: LoadedSpec) -> list[ApiChange]:
    """Return a stable list of relevant compatibility changes."""
    changes = [*_compare_operations(old, new), *_compare_component_schemas(old, new)]
    order = {"breaking": 0, "warning": 1, "compatible": 2}
    return sorted(changes, key=lambda item: (order[item.kind], item.location, item.category))
