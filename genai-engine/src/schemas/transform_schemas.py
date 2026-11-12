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
from utils.trace_serializer import DEFAULT_MAX_CHARS, MIN_MAX_CHARS

# OPEN DECISION (maintainers): whether a variable may match on span_kind alone.
# True: span_name becomes optional, so transform responses can return a null
# span_name, which oasdiff flags as breaking for clients that read it as a
# string. False: span_name stays required as in arthur_common (span_kind only
# narrows it, and 'current' needs a name too); no client break, and span_kind-only
# waits for an arthur_common release that makes span_name optional.
SPAN_KIND_ONLY_VARIABLES = True


class TransformSpanSelector(str, Enum):
    FIRST = "first"
    LAST = "last"
    ALL = "all"
    # The span a span-scope continuous eval is judging; only that eval sets one.
    CURRENT = "current"


class TransformVariableSource(str, Enum):
    # Read one attribute from the matching span(s).
    SPAN = "span"
    # The whole trace as judge-ready text (utils.trace_serializer).
    TRACE = "trace"


class TraceTransformVariableDefinition(
    AcceptsCommonModel,
    CommonTraceTransformVariableDefinition,
):
    if SPAN_KIND_ONLY_VARIABLES:
        span_name: Optional[str] = Field(  # type: ignore[assignment]
            default=None,
            description=(
                "Name of the span to read from. Optional when span_kind is set; at "
                "least one of the two is required."
            ),
        )
    span_kind: Optional[str] = Field(
        default=None,
        description=(
            "Kind of the span to read from, such as TOOL or LLM. Alone it matches every "
            "span of that kind; with span_name it narrows the named spans."
        ),
    )
    source: TransformVariableSource = Field(
        default=TransformVariableSource.SPAN,
        description=(
            "Where the value comes from: 'span' (the default) reads attribute_path from "
            "the matching span(s); 'trace' is the whole trace as text for a judge, every "
            "span in tree order with its inputs, outputs, tool calls and errors, cut to "
            "max_chars. With 'trace' the span fields are not used and attribute_path is "
            "ignored (send an empty string)."
        ),
    )
    max_chars: Optional[int] = Field(
        default=None,
        ge=MIN_MAX_CHARS,
        description=(
            f"Size budget of a 'trace' value in characters; defaults to {DEFAULT_MAX_CHARS}. "
            "Over budget, the text says what was cut."
        ),
    )
    span_selector: TransformSpanSelector = Field(
        default=TransformSpanSelector.FIRST,
        description=(
            "Which span to read when several match: 'first' (the default) or 'last' in "
            "tree order (depth-first, siblings by start time then span id), so 'last' "
            "is a retried tool call; 'all' reads every match in tree order and joins "
            "their values into one block, each headed by its span id. 'current' "
            "reads the span a span-scope continuous eval is judging (span_name and "
            "span_kind, if set, must match it); elsewhere it finds no span."
        ),
    )

    @model_validator(mode="after")
    def _needs_span_name_or_kind(self) -> "TraceTransformVariableDefinition":
        if self.source == TransformVariableSource.TRACE:
            return self
        if (
            not self.span_name
            and not self.span_kind
            and self.span_selector != TransformSpanSelector.CURRENT
        ):
            raise ValueError(
                f"Variable {self.variable_name} needs a span_name, a span_kind or both.",
            )
        return self

    def describe_spans(self) -> str:
        """How a skip message names the spans this variable looks for."""
        if self.source == TransformVariableSource.TRACE:
            return "the trace"
        if self.span_name and self.span_kind:
            return f"{self.span_name} ({self.span_kind})"
        if self.span_name:
            return self.span_name
        if self.span_kind:
            return f"any {self.span_kind} span"
        return "the judged span"


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
