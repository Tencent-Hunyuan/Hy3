from __future__ import annotations

from pathlib import Path

import pytest

from hy3_api_guardian.errors import SpecInputError
from hy3_api_guardian.settings import Settings
from hy3_api_guardian.spec_loader import compact_for_model, load_spec, resolve_local_object

VALID_SPEC = """
openapi: 3.1.0
info:
  title: Demo
  version: 1.0.0
paths:
  /health:
    get:
      operationId: health
      responses:
        '200':
          description: ok
"""


def test_load_inline_spec(settings: Settings) -> None:
    loaded = load_spec(spec_path=None, spec_text=VALID_SPEC, settings=settings)
    assert loaded.title == "Demo"
    assert loaded.operation_count == 1


def test_requires_exactly_one_input(settings: Settings) -> None:
    with pytest.raises(SpecInputError, match="exactly one"):
        load_spec(spec_path=None, spec_text=None, settings=settings)
    with pytest.raises(SpecInputError, match="exactly one"):
        load_spec(spec_path="a.yaml", spec_text=VALID_SPEC, settings=settings)


def test_rejects_path_outside_allowed_root(settings: Settings, tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-openapi.yaml"
    outside.write_text(VALID_SPEC, encoding="utf-8")
    try:
        with pytest.raises(SpecInputError, match="outside HY3_ALLOWED_ROOT"):
            load_spec(spec_path=str(outside), spec_text=None, settings=settings)
    finally:
        outside.unlink(missing_ok=True)


def test_rejects_openapi_v2(settings: Settings) -> None:
    with pytest.raises(SpecInputError, match=r"OpenAPI 3\.x"):
        load_spec(
            spec_path=None,
            spec_text='swagger: "2.0"\ninfo: {title: Demo, version: 1}\npaths: {}',
            settings=settings,
        )


def test_compact_projection_redacts_bearer_token(settings: Settings) -> None:
    loaded = load_spec(
        spec_path=None,
        spec_text=VALID_SPEC.replace("description: ok", "description: 'Bearer abcdefghijklmnop'"),
        settings=settings,
    )
    compact = compact_for_model(loaded, 30_000)
    assert "abcdefghijklmnop" not in compact
    assert "[REDACTED]" in compact


def test_rejects_yaml_aliases(settings: Settings) -> None:
    malicious = """
openapi: 3.1.0
info: {title: Demo, version: 1.0.0}
paths: &paths
  /health: {get: {responses: {'200': {description: ok}}}}
x-copy: *paths
"""
    with pytest.raises(SpecInputError, match="aliases"):
        load_spec(spec_path=None, spec_text=malicious, settings=settings)


def test_resolves_local_component_reference_without_fetching_remote(settings: Settings) -> None:
    loaded = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.1.0
info: {title: References, version: 1.0.0}
paths: {}
components:
  parameters:
    TraceId:
      {name: X-Trace-Id, in: header, schema: {type: string}}
""",
        settings=settings,
    )
    resolved = resolve_local_object(loaded.document, {"$ref": "#/components/parameters/TraceId"})
    assert resolved and resolved["name"] == "X-Trace-Id"
    assert resolve_local_object(loaded.document, {"$ref": "https://example.test/p.yaml"}) is None


def test_compact_projection_includes_referenced_component_sections(settings: Settings) -> None:
    loaded = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.1.0
info: {title: References, version: 1.0.0}
paths:
  /pets:
    post:
      requestBody: {$ref: '#/components/requestBodies/PetBody'}
      responses: {'201': {description: created}}
components:
  requestBodies:
    PetBody:
      required: true
      content:
        application/json:
          schema: {type: object}
""",
        settings=settings,
    )
    compact = compact_for_model(loaded, 30_000)
    assert '"requestBodies"' in compact
    assert '"PetBody"' in compact
