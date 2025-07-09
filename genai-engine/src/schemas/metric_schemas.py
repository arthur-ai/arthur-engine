from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.enums import ToolClassEnum


class RelevanceMetricConfig(BaseModel):
    """Configuration for relevance metrics including QueryRelevance and ResponseRelevance"""

    relevance_threshold: Optional[float] = Field(
        default=None,
        description="Threshold for determining relevance when not using LLM judge",
    )
    use_llm_judge: bool = Field(
        default=True, description="Whether to use LLM as a judge for relevance scoring"
    )


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


class MetricRequest(BaseModel):
    system_prompt: Optional[str] = Field(
        description="System prompt to be used by GenAI Engine for computing metrics.",
        default=None,
    )
    user_query: Optional[str] = Field(
        description="User query to be used by GenAI Engine for computing metrics.",
        default=None,
    )
    context: List[dict] = Field(
        description="Conversation history and additional context to be used by GenAI Engine for computing metrics.",
        default=[],
        example=[
            {"role": "user", "value": "What is the weather in Tokyo?"},
            {"role": "assistant", "value": "WeatherTool", "args": {"city": "Tokyo"}},
            {
                "role": "tool",
                "value": '[{"name": "WeatherTool", "result": {"temperature": "20°C", "humidity": "50%", "condition": "sunny"}}]',
            },
            {
                "role": "assistant",
                "value": "The weather in Tokyo is sunny and the temperature is 20°C.",
            },
        ],
    )
    response: Optional[str] = Field(
        description="Response to be used by GenAI Engine for computing metrics.",
        default=None,
    )
