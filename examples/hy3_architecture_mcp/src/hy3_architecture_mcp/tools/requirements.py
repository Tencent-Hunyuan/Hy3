"""clarify_requirements tool."""

from __future__ import annotations

import json

from .._runtime import get_client, load_prompt
from ..schemas import ClarifyRequirementsInput, ClarifyRequirementsOutput

PROMPT_NAME = "clarify_requirements"


def _build_user_prompt(data: ClarifyRequirementsInput) -> str:
    return json.dumps(
        {
            "requirement": data.requirement,
            "project_context": data.project_context,
            "constraints": data.constraints,
            "max_questions": data.max_questions,
            "output_language": data.output_language,
        },
        ensure_ascii=False,
        indent=2,
    )


async def run(data: ClarifyRequirementsInput) -> ClarifyRequirementsOutput:
    client = get_client()
    result = await client.generate_structured(
        system_prompt=load_prompt(PROMPT_NAME),
        user_prompt=_build_user_prompt(data),
        response_model=ClarifyRequirementsOutput,
    )
    # Enforce the max_questions cap on the model output.
    if len(result.clarifying_questions) > data.max_questions:
        result = result.model_copy(
            update={"clarifying_questions": result.clarifying_questions[: data.max_questions]}
        )
    return result
