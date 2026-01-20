from pydantic import BaseModel, Field


class ReasonedScore(BaseModel):
    """
    Response format schema for llm eval runs
    """

    reason: str = Field(
        ...,
        description="Explanation for how you arrived at this answer.",
    )
    score: int = Field(..., ge=0, le=1, description="Binary score between 0 and 1")
