from __future__ import annotations

from hy3_api_guardian.diff_engine import compare_specs
from hy3_api_guardian.settings import Settings
from hy3_api_guardian.spec_loader import load_spec

OLD = """
openapi: 3.1.0
info: {title: Demo, version: 1.0.0}
paths:
  /users/{id}:
    get:
      operationId: getUser
      parameters:
        - {name: id, in: path, required: true, schema: {type: integer}}
      responses:
        '200': {description: ok}
  /users:
    post:
      operationId: createUser
      requestBody: {required: false}
      responses:
        '201': {description: created}
components:
  schemas:
    User:
      type: object
      required: [id]
      properties:
        id: {type: integer}
        nickname: {type: string}
"""

NEW = """
openapi: 3.1.0
info: {title: Demo, version: 2.0.0}
paths:
  /users:
    get:
      operationId: listUsers
      parameters:
        - {name: limit, in: query, required: true, schema: {type: integer}}
      responses:
        '200': {description: ok}
    post:
      operationId: createUser
      requestBody: {required: true}
      responses:
        '202': {description: accepted}
components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id: {type: string}
        email: {type: string}
"""


def test_compare_specs_classifies_breaking_and_compatible_changes(settings: Settings) -> None:
    old = load_spec(spec_path=None, spec_text=OLD, settings=settings)
    new = load_spec(spec_path=None, spec_text=NEW, settings=settings)
    changes = compare_specs(old, new)
    categories = {item.category for item in changes}
    assert "operation_removed" in categories
    assert "operation_added" in categories
    assert "request_body_required" in categories
    assert "response_removed" in categories
    assert "required_property_added" in categories
    assert "schema_property_type" in categories
    assert changes[0].kind == "breaking"


def test_compare_specs_resolves_referenced_parameters_and_request_bodies(
    settings: Settings,
) -> None:
    old = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.1.0
info: {title: References, version: 1.0.0}
paths:
  /pets:
    post:
      parameters: [{$ref: '#/components/parameters/TraceId'}]
      requestBody: {$ref: '#/components/requestBodies/PetBody'}
      responses: {'201': {description: created}}
components:
  parameters:
    TraceId: {name: X-Trace-Id, in: header, required: false, schema: {type: string}}
  requestBodies:
    PetBody: {required: false}
""",
        settings=settings,
    )
    new = load_spec(
        spec_path=None,
        spec_text="""
openapi: 3.1.0
info: {title: References, version: 2.0.0}
paths:
  /pets:
    post:
      parameters: [{$ref: '#/components/parameters/TraceId'}]
      requestBody: {$ref: '#/components/requestBodies/PetBody'}
      responses: {'201': {description: created}}
components:
  parameters:
    TraceId: {name: X-Trace-Id, in: header, required: true, schema: {type: string}}
  requestBodies:
    PetBody: {required: true}
""",
        settings=settings,
    )
    categories = {change.category for change in compare_specs(old, new)}
    assert "parameter_required" in categories
    assert "request_body_required" in categories
