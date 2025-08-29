from typing import Optional

from arthur_common.models.metric_schemas import (
    QueryRelevanceMetric,
    ResponseRelevanceMetric,
)
from pydantic import BaseModel

from schemas.enums import ToolClassEnum


# Internal to genai-engine
class ToolSelectionCorrectnessMetric(BaseModel):
    tool_selection: ToolClassEnum
    tool_selection_reason: str
    tool_usage: ToolClassEnum
    tool_usage_reason: str


# Internal to genai-engine
class MetricScoreDetails(BaseModel):
    query_relevance: Optional[QueryRelevanceMetric] = None
    response_relevance: Optional[ResponseRelevanceMetric] = None
    rag_score: Optional[float] = None
    persona_alignment: Optional[float] = None
    tool_selection: Optional[ToolSelectionCorrectnessMetric] = None
