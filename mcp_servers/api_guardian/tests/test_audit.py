from __future__ import annotations

from hy3_api_guardian.audit import audit_locally
from hy3_api_guardian.settings import Settings
from hy3_api_guardian.spec_loader import load_spec

INSECURE_SPEC = """
openapi: 3.0.3
info: {title: Demo, version: 1.0.0}
servers:
  - url: http://api.example.test
paths:
  /users/{userId}:
    get:
      operationId: duplicate
      responses: {}
    delete:
      operationId: duplicate
      parameters:
        - {name: userId, in: path, required: false, schema: {type: string}}
      responses:
        '204': {description: deleted}
"""


def test_local_audit_finds_high_value_issues(settings: Settings) -> None:
    spec = load_spec(spec_path=None, spec_text=INSECURE_SPEC, settings=settings)
    findings = audit_locally(spec)
    categories = {item.category for item in findings}
    assert "transport_security" in categories
    assert "operation_id" in categories
    assert "path_parameter" in categories
    assert "response_contract" in categories
    assert any(item.severity == "high" for item in findings)


def test_local_audit_resolves_referenced_path_parameter(settings: Settings) -> None:
    spec = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.1.0
info: {title: References, version: 1.0.0, description: demo}
servers: [{url: https://api.example.test}]
paths:
  /pets/{petId}:
    get:
      operationId: getPet
      summary: Get a pet
      parameters:
        - {$ref: '#/components/parameters/PetId'}
      responses: {'200': {description: ok}}
components:
  parameters:
    PetId:
      {name: petId, in: path, required: true, schema: {type: string}}
""",
        settings=settings,
    )
    findings = audit_locally(spec)
    assert not any(item.category == "path_parameter" for item in findings)


def test_local_audit_resolves_referenced_path_item(settings: Settings) -> None:
    spec = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.1.0
info: {title: References, version: 1.0.0, description: demo}
servers: [{url: https://api.example.test}]
paths:
  /pets/{petId}:
    {$ref: '#/components/pathItems/Pet'}
components:
  pathItems:
    Pet:
      get:
        operationId: getPet
        summary: Get a pet
        parameters:
          - {name: petId, in: path, required: true, schema: {type: string}}
        responses: {'200': {description: ok}}
""",
        settings=settings,
    )
    findings = audit_locally(spec)
    assert not any(item.category == "path_parameter" for item in findings)
    assert not any(item.category == "operation_id" for item in findings)


def test_local_audit_does_not_trust_deceptive_localhost_server(settings: Settings) -> None:
    spec = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.0.3
info: {title: Deceptive host, version: 1.0.0, description: demo}
servers: [{url: http://localhost.evil.example}]
paths: {}
""",
        settings=settings,
    )
    findings = audit_locally(spec)
    assert any(item.category == "transport_security" for item in findings)


def test_local_audit_allows_ipv6_loopback_server(settings: Settings) -> None:
    spec = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.0.3
info: {title: Loopback, version: 1.0.0, description: demo}
servers: [{url: 'http://[::1]:8000'}]
paths: {}
""",
        settings=settings,
    )
    findings = audit_locally(spec)
    assert not any(item.category == "transport_security" for item in findings)


def test_local_audit_reports_malformed_server_without_crashing(settings: Settings) -> None:
    spec = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.0.3
info: {title: Malformed server, version: 1.0.0, description: demo}
servers: [{url: 'http://['}]
paths: {}
""",
        settings=settings,
    )
    findings = audit_locally(spec)
    assert any(item.category == "server" and "malformed" in item.message for item in findings)
