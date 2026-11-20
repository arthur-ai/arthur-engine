"""Trace transform definitions with a value source per variable.

The shared models in arthur_common read one attribute from spans named span_name.
The engine extends them here so a variable can instead be the whole trace as
judge-ready text (source='trace'), for judges that need to see every step, such as
a retry. Existing definitions keep working: a variable without source reads spans.
"""

from enum import Enum
from typing import Any, Optional

from arthur_common.models.task_eval_schemas import (
    ListTraceTransformsResponse as CommonListTraceTransformsResponse,
)
from arthur_common.models.task_eval_schemas import (
    TraceTransformDefinition as CommonTraceTransformDefinition,
)
from arthur_common.models.task_eval_schemas import (
    TraceTransformResponse as CommonTraceTransformResponse,
)
from arthur_common.models.task_eval_schemas import (
    TraceTransformVariableDefinition as CommonTraceTransformVariableDefinition,
)
from pydantic import BaseModel, Field, model_validator

from utils.trace_serializer import DEFAULT_MAX_CHARS, MIN_MAX_CHARS


class _AcceptsCommonModel(BaseModel):
    """Lets code that still builds the arthur_common model pass it where the
    engine model is expected."""

    @model_validator(mode="before")
    @classmethod
    def _from_common_model(cls, data: Any) -> Any:
        if isinstance(data, BaseModel) and not isinstance(data, cls):
            return data.model_dump()
        return data


class TransformVariableSource(str, Enum):
    SPAN = "span"
    TRACE = "trace"


class TraceTransformVariableDefinition(
    _AcceptsCommonModel,
    CommonTraceTransformVariableDefinition,
):
    source: TransformVariableSource = Field(
        default=TransformVariableSource.SPAN,
        description=(
            "Where the value comes from. 'span' (the default) reads attribute_path from "
            "the spans named span_name; when several match, every match is read in "
            "trace order, each headed by its span id. 'trace' is the whole trace as "
            "judge-ready text, every span in tree order; span_name and attribute_path "
            "are not used and can be empty."
        ),
    )
    max_chars: Optional[int] = Field(
        default=None,
        ge=MIN_MAX_CHARS,
        description=(
            "The most characters the value may take: the whole trace's text for "
            "source='trace', or the joined value when several spans match for "
            "source='span' (a single match is never cut). Over it, the value says "
            f"what was shortened or left out. Defaults to {DEFAULT_MAX_CHARS:,}."
        ),
    )


class TraceTransformDefinition(_AcceptsCommonModel, CommonTraceTransformDefinition):
    variables: list[TraceTransformVariableDefinition] = Field(  # type: ignore[assignment]
        description="List of variable extraction rules.",
    )


class TraceTransformResponse(_AcceptsCommonModel, CommonTraceTransformResponse):
    definition: TraceTransformDefinition = Field(
        description="Latest version of the transform definition.",
    )


class ListTraceTransformsResponse(
    _AcceptsCommonModel,
    CommonListTraceTransformsResponse,
):
    transforms: list[TraceTransformResponse] = Field(  # type: ignore[assignment]
        description="List of transforms for the task.",
    )
