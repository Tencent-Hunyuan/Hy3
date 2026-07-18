"""create_implementation_plan tool."""

from __future__ import annotations

import json

from .._runtime import get_client, load_prompt
from ..schemas import CreateImplementationPlanInput, CreateImplementationPlanOutput

PROMPT_NAME = "implementation_plan"


def _build_user_prompt(data: CreateImplementationPlanInput) -> str:
    return json.dumps(
        {
            "proposal": data.proposal,
            "team_size": data.team_size,
            "target_days": data.target_days,
            "available_roles": data.available_roles,
            "output_language": data.output_language,
        },
        ensure_ascii=False,
        indent=2,
    )


async def run(data: CreateImplementationPlanInput) -> CreateImplementationPlanOutput:
    client = get_client()
    return await client.generate_structured(  # type: ignore[return-value]
        system_prompt=load_prompt(PROMPT_NAME),
        user_prompt=_build_user_prompt(data),
        response_model=CreateImplementationPlanOutput,
    )
