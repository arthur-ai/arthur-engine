from arthur_common.models.task_eval_schemas import LLMEval
from pydantic import BaseModel, Field

__all__ = ["LLMEval", "ReasonedScore"]


class ReasonedScore(BaseModel):
    """
    Response format schema for llm eval runs
    """

    reason: str = Field(
        ...,
        description="Explanation for how you arrived at this answer.",
    )
    score: int = Field(..., ge=0, le=1, description="Binary score between 0 and 1")
