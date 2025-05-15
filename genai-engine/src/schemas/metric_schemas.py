from typing import List, Optional

from pydantic import BaseModel
from schemas.enums import MetricType, ToolClassEnum
from schemas.scorer_schemas import Example


class QueryRelevanceMetric(BaseModel):
    bert_f_score: float
    reranker_relevance_score: float
    llm_relevance_score: Optional[float] = None
    reason: Optional[str] = None
    refinement: Optional[str] = None


class ResponseRelevanceMetric(BaseModel):
    bert_f_score: float
    reranker_relevance_score: float
    llm_relevance_score: Optional[float] = None
    reason: Optional[str] = None
    refinement: Optional[str] = None


class ToolSelectionCorrectnessMetric(BaseModel):
    tool_selection: ToolClassEnum
    tool_selection_reason: str
    tool_usage: ToolClassEnum
    tool_usage_reason: str


class MetricScoreDetails(BaseModel):
    query_relevance: Optional[QueryRelevanceMetric] = None
    response_relevance: Optional[ResponseRelevanceMetric] = None
    rag_score: Optional[float] = None
    persona_alignment: Optional[float] = None
    tool_selection: Optional[ToolSelectionCorrectnessMetric] = None


class MetricScore(BaseModel):
    metric: MetricType
    details: MetricScoreDetails
    prompt_tokens: int = 0
    completion_tokens: int = 0


class MetricRequest(BaseModel):
    metric_type: MetricType
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    use_llm_judge: Optional[bool] = False
    scoring_text: Optional[str] = None
    context: Optional[str] = None
    examples: Optional[List[Example]] = None
    hint: Optional[str] = None 