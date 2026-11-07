"""Trace transform definitions with a per-variable span selector.

The shared models in arthur_common have no way to say which span to read when
several match a variable's span_name, so the engine extends them here. Existing
definitions keep working: a variable without span_selector reads the first match,
as before.
"""

from enum import Enum

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
from pydantic import Field

from schemas.model_compat import AcceptsCommonModel


class TransformSpanSelector(str, Enum):
    FIRST = "first"
    LAST = "last"
    ALL = "all"


class TraceTransformVariableDefinition(
    AcceptsCommonModel,
    CommonTraceTransformVariableDefinition,
):
    span_selector: TransformSpanSelector = Field(
        default=TransformSpanSelector.FIRST,
        description=(
            "Which span to read when several are named span_name: 'first' (the default) "
            "is the first match in the trace; 'last' is the one that started last, such "
            "as a retried tool call; 'all' reads every match in start-time order and "
            "joins their values into one block, each headed by its span id."
        ),
    )


class TraceTransformDefinition(AcceptsCommonModel, CommonTraceTransformDefinition):
    variables: list[TraceTransformVariableDefinition] = Field(  # type: ignore[assignment]
        description="List of variable extraction rules.",
    )


class TraceTransformResponse(AcceptsCommonModel, CommonTraceTransformResponse):
    definition: TraceTransformDefinition = Field(
        description="Latest version of the transform definition.",
    )


class ListTraceTransformsResponse(
    AcceptsCommonModel,
    CommonListTraceTransformsResponse,
):
    transforms: list[TraceTransformResponse] = Field(  # type: ignore[assignment]
        description="List of transforms for the task.",
    )
