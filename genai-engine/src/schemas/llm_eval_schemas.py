from typing import Any, Optional

from arthur_common.models.task_eval_schemas import Eval
from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Eval", "ReasonedScore"]


class ReasonedScore(BaseModel):
    """
    Response format schema for llm eval runs
    """

    reason: str = Field(
        ...,
        description="Explanation for how you arrived at this answer.",
    )
    score: int = Field(..., ge=0, le=1, description="Binary score between 0 and 1")
    label: Optional[str] = Field(
        default=None,
        description=(
            "A short category for the result when the instructions define categories "
            "(e.g. 'wrong_tool'); otherwise null."
        ),
    )

    # Listed as required (nullable) in the schema sent to the model, because strict
    # structured outputs need every field listed; a reply without it still parses.
    model_config = ConfigDict(json_schema_extra=lambda schema: _require_all(schema))


def _require_all(schema: dict[str, Any]) -> None:
    schema["required"] = list(schema.get("properties", {}))
