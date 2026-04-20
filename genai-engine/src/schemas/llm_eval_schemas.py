from datetime import datetime
from typing import Any, List, Optional

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


class MLEval(BaseModel):
    """Internal representation of an ML-type eval (pii, toxicity, prompt_injection, etc.)."""

    name: str
    eval_type: str
    variables: List[str] = []
    config: Optional[Any] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None
    version: int
    tags: List[str] = []
