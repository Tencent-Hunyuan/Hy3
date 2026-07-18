"""review_technical_proposal tool."""

from __future__ import annotations

import json

from .._runtime import get_client, load_prompt
from ..schemas import (
    DEFAULT_REVIEW_DIMENSIONS,
    ReviewTechnicalProposalInput,
    ReviewTechnicalProposalOutput,
)

PROMPT_NAME = "review_proposal"


def _build_user_prompt(data: ReviewTechnicalProposalInput) -> str:
    dimensions = data.review_dimensions or list(DEFAULT_REVIEW_DIMENSIONS)
    return json.dumps(
        {
            "proposal": data.proposal,
            "requirements": data.requirements,
            "review_dimensions": dimensions,
            "risk_threshold": data.risk_threshold,
            "output_language": data.output_language,
        },
        ensure_ascii=False,
        indent=2,
    )


async def run(data: ReviewTechnicalProposalInput) -> ReviewTechnicalProposalOutput:
    client = get_client()
    return await client.generate_structured(  # type: ignore[return-value]
        system_prompt=load_prompt(PROMPT_NAME),
        user_prompt=_build_user_prompt(data),
        response_model=ReviewTechnicalProposalOutput,
    )
