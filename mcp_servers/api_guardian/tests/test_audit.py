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
