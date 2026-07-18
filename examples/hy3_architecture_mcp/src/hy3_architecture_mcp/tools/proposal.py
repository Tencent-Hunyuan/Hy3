"""generate_technical_proposal tool."""

from __future__ import annotations

import json

from .._runtime import get_client, load_prompt
from ..schemas import GenerateTechnicalProposalInput, GenerateTechnicalProposalOutput

PROMPT_NAME = "generate_proposal"


def _build_user_prompt(data: GenerateTechnicalProposalInput) -> str:
    return json.dumps(
        {
            "requirements": data.requirements,
            "project_context": data.project_context,
            "preferred_stack": data.preferred_stack,
            "constraints": data.constraints,
            "proposal_depth": data.proposal_depth,
            "output_language": data.output_language,
        },
        ensure_ascii=False,
        indent=2,
    )


async def run(data: GenerateTechnicalProposalInput) -> GenerateTechnicalProposalOutput:
    client = get_client()
    return await client.generate_structured(  # type: ignore[return-value]
        system_prompt=load_prompt(PROMPT_NAME),
        user_prompt=_build_user_prompt(data),
        response_model=GenerateTechnicalProposalOutput,
    )
