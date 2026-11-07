"""Agentic annotation responses with the span and category an annotation is about.

The shared models in arthur_common describe whole-trace, score-only annotations,
so the engine extends them here.
"""

from typing import List, Optional

from arthur_common.models.response_schemas import (
    AgenticAnnotationResponse as CommonAgenticAnnotationResponse,
)
from arthur_common.models.response_schemas import (
    ListAgenticAnnotationsResponse as CommonListAgenticAnnotationsResponse,
)
from pydantic import Field

from schemas.model_compat import AcceptsCommonModel

ANNOTATION_LABEL_MAX_LENGTH = 100


class AgenticAnnotationResponse(AcceptsCommonModel, CommonAgenticAnnotationResponse):
    span_id: Optional[str] = Field(
        default=None,
        description="Span the annotation is about. Null for the whole trace.",
    )
    label: Optional[str] = Field(
        default=None,
        description=(
            "Category of the result, such as 'wrong_tool', given by a person or by a "
            "judge whose instructions define categories."
        ),
    )


class ListAgenticAnnotationsResponse(
    AcceptsCommonModel,
    CommonListAgenticAnnotationsResponse,
):
    annotations: List[AgenticAnnotationResponse] = Field(  # type: ignore[assignment]
        description="List of annotations",
    )
