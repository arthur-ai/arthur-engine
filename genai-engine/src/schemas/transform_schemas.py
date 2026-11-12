"""Trace transform definitions with a per-variable span selector and span kind.

The shared models in arthur_common have no way to say which span to read when
several match a variable, or to match spans by kind, so the engine extends them
here. Existing definitions keep working: a variable without span_selector reads
the first match in tree order, and span_name alone still picks the spans.
"""

from enum import Enum
from typing import Optional

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
from pydantic import Field, model_validator

from schemas.model_compat import AcceptsCommonModel


class TransformSpanSelector(str, Enum):
    FIRST = "first"
    LAST = "last"
    ALL = "all"


class TraceTransformVariableDefinition(
    AcceptsCommonModel,
    CommonTraceTransformVariableDefinition,
):
    span_name: Optional[str] = Field(  # type: ignore[assignment]
        default=None,
        description=(
            "Name of the span to read from. Optional when span_kind is set; at least "
            "one of the two is required."
        ),
    )
    span_kind: Optional[str] = Field(
        default=None,
        description=(
            "Kind of the span to read from, such as TOOL or LLM. Alone it matches every "
            "span of that kind; with span_name it narrows the named spans."
        ),
    )
    span_selector: TransformSpanSelector = Field(
        default=TransformSpanSelector.FIRST,
        description=(
            "Which span to read when several match: 'first' (the default) or 'last' in "
            "tree order (depth-first, siblings by start time then span id), so 'last' "
            "is a retried tool call; 'all' reads every match in tree order and joins "
            "their values into one block, each headed by its span id."
        ),
    )

    @model_validator(mode="after")
    def _needs_span_name_or_kind(self) -> "TraceTransformVariableDefinition":
        if not self.span_name and not self.span_kind:
            raise ValueError(
                f"Variable {self.variable_name} needs a span_name, a span_kind or both.",
            )
        return self

    def describe_spans(self) -> str:
        """How a skip message names the spans this variable looks for."""
        if self.span_name and self.span_kind:
            return f"{self.span_name} ({self.span_kind})"
        if self.span_name:
            return self.span_name
        return f"any {self.span_kind} span"


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
