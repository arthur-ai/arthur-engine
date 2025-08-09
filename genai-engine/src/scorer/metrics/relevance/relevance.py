import logging
from typing import Optional, Tuple

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.json import JsonOutputParser
from pydantic import BaseModel, Field

from schemas.enums import MetricType
from schemas.internal_schemas import MetricResult
from schemas.metric_schemas import (
    MetricRequest,
    MetricScoreDetails,
    QueryRelevanceMetric,
    ResponseRelevanceMetric,
)
from scorer.llm_client import get_llm_executor
from scorer.metrics.relevance.prompt_templates import (
    RESPONSE_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE,
    RESPONSE_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE,
    USER_QUERY_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE,
    USER_QUERY_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE,
)
from scorer.scorer import MetricScorer
from utils.model_load import get_bert_scorer, get_relevance_reranker
from utils.utils import relevance_models_enabled

logger = logging.getLogger()


def round_score(score: float) -> float:
    """Rounds a score to consistent precision for all relevance metrics."""
    return round(float(score), 2)


# Unified schema for both query and response relevance
class RelevanceResponseSchema(BaseModel):
    relevance_score: float = Field(
        description="A numerical value where 1 means 'highly relevant' and 0 means 'completely irrelevant'",
    )
    justification: str = Field(
        description="Explanation of why the query/response is relevant or not",
    )
    suggested_refinement: str = Field(
        description="If the query/response is somewhat relevant but not fully aligned, suggest a better phrasing. 'None' if not applicable",
    )


def get_relevance_chain(metric_type: MetricType, temperature: float = 0.0):
    """Get the appropriate relevance chain based on metric type and structured output support"""
    model = get_llm_executor().get_gpt_model(chat_temperature=temperature)

    # Select template based on metric type
    if metric_type == MetricType.QUERY_RELEVANCE:
        structured_template = USER_QUERY_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE
        legacy_template = USER_QUERY_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE
        input_vars = ["system_prompt", "user_query"]
    else:  # RESPONSE_RELEVANCE
        structured_template = RESPONSE_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE
        legacy_template = RESPONSE_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE
        input_vars = ["system_prompt", "user_query", "response"]

    # Use structured outputs if supported, otherwise fall back to legacy
    if get_llm_executor().supports_structured_outputs():
        pt = PromptTemplate(input_variables=input_vars, template=structured_template)
        return pt | model.with_structured_output(RelevanceResponseSchema)
    else:
        parser = JsonOutputParser(pydantic_object=RelevanceResponseSchema)
        pt = PromptTemplate(
            input_variables=input_vars,
            partial_variables={"format_instructions": parser.get_format_instructions()},
            template=legacy_template,
        )
        return pt | model | parser


class BaseRelevanceScorer(MetricScorer):
    """Base class for relevance scorers with common functionality"""

    def __init__(self, metric_type: MetricType):
        super().__init__()
        self.metric_type = metric_type
        self.relevance_reranker = get_relevance_reranker()
        self.bert_scorer = get_bert_scorer()

    def _should_return_defaults(self, use_llm_judge: bool) -> bool:
        """Check if we should return default values (no models, no LLM judge)"""
        return not use_llm_judge and not relevance_models_enabled()

    def _get_model_scores(
        self,
        request: MetricRequest,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Get scores from BERT and reranker models if available"""
        bert_f_score = None
        reranker_score = None

        if relevance_models_enabled():
            # Build input for both models
            model_input = self._build_model_input(request)

            # Get reranker score
            if self.relevance_reranker is not None:
                res = self.relevance_reranker(model_input)
                reranker_score = res["score"]

            # Get BERT score
            if self.bert_scorer is not None:
                bert_f_score = self._get_bert_score(model_input)

        return bert_f_score, reranker_score

    def _get_bert_score(self, model_input: dict) -> Optional[float]:
        """Get BERT score using the same input format as reranker"""
        try:
            _, _, f = self.bert_scorer.score(
                [model_input["text_pair"]],
                [model_input["text"]],
                verbose=False,
            )
            return float(f.mean(dim=0))
        except Exception:
            return None

    def _get_llm_scores(
        self,
        request: MetricRequest,
    ) -> Tuple[Optional[float], Optional[str], Optional[str], int, int]:
        """Get scores from LLM judge"""
        relevance_chain = get_relevance_chain(self.metric_type)
        chain_call = lambda: relevance_chain.invoke(self._build_llm_input(request))

        try:
            llm_judge_response, token_consumption = get_llm_executor().execute(
                chain_call,
                f"{self.metric_type.value} Check",
            )
        except Exception:
            return None, None, None, 0, 0

        # Handle both structured output (Pydantic model) and legacy (dict) responses
        if isinstance(llm_judge_response, RelevanceResponseSchema):
            relevance_score_llm = llm_judge_response.relevance_score
            justification = llm_judge_response.justification
            suggested_refinement = llm_judge_response.suggested_refinement
        else:
            relevance_score_llm = llm_judge_response["relevance_score"]
            justification = llm_judge_response["justification"]
            suggested_refinement = llm_judge_response["suggested_refinement"]

        return (
            relevance_score_llm,
            justification,
            suggested_refinement,
            token_consumption.prompt_tokens,
            token_consumption.completion_tokens,
        )

    def _create_metric_details(
        self,
        bert_f_score: Optional[float],
        reranker_score: Optional[float],
        llm_score: Optional[float] = None,
        reason: Optional[str] = None,
        refinement: Optional[str] = None,
    ) -> MetricScoreDetails:
        """Create metric details with proper rounding"""
        if self.metric_type == MetricType.QUERY_RELEVANCE:
            return MetricScoreDetails(
                query_relevance=QueryRelevanceMetric(
                    bert_f_score=(
                        round_score(bert_f_score) if bert_f_score is not None else None
                    ),
                    reranker_relevance_score=(
                        round_score(reranker_score)
                        if reranker_score is not None
                        else None
                    ),
                    llm_relevance_score=(
                        round_score(llm_score) if llm_score is not None else None
                    ),
                    reason=reason,
                    refinement=refinement,
                ),
            )
        else:  # RESPONSE_RELEVANCE
            return MetricScoreDetails(
                response_relevance=ResponseRelevanceMetric(
                    bert_f_score=(
                        round_score(bert_f_score) if bert_f_score is not None else None
                    ),
                    reranker_relevance_score=(
                        round_score(reranker_score)
                        if reranker_score is not None
                        else None
                    ),
                    llm_relevance_score=(
                        round_score(llm_score) if llm_score is not None else None
                    ),
                    reason=reason,
                    refinement=refinement,
                ),
            )

    def _build_model_input(self, request: MetricRequest) -> dict:
        """Build input for both reranker and BERT models"""
        raise NotImplementedError("Subclasses must implement this method")

    def _build_llm_input(self, request: MetricRequest) -> dict:
        """Build input for the LLM judge"""
        raise NotImplementedError("Subclasses must implement this method")

    def score(self, request: MetricRequest, config: dict) -> MetricResult:
        """Generic scoring method that works for both query and response relevance"""
        use_llm_judge = config.get("use_llm_judge", True)

        # If both LLM judge is disabled and models are disabled, return defaults
        if self._should_return_defaults(use_llm_judge):
            metric_details = self._create_metric_details(None, None)
            return MetricResult(
                id="",
                metric_type=self.metric_type,
                details=metric_details,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
            )

        # Get model scores
        bert_f_score, reranker_score = self._get_model_scores(request)

        # Create metric details
        metric_details = self._create_metric_details(bert_f_score, reranker_score)

        # Get LLM scores if requested
        if use_llm_judge:
            llm_score, reason, refinement, prompt_tokens, completion_tokens = (
                self._get_llm_scores(request)
            )
            metric_details = self._create_metric_details(
                bert_f_score,
                reranker_score,
                llm_score,
                reason,
                refinement,
            )

            return MetricResult(
                id="",
                metric_type=self.metric_type,
                details=metric_details,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=0,
            )
        else:
            return MetricResult(
                id="",
                metric_type=self.metric_type,
                details=metric_details,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
            )


class UserQueryRelevanceScorer(BaseRelevanceScorer):
    """Scorer for evaluating user query relevance against system prompt"""

    def __init__(self):
        super().__init__(MetricType.QUERY_RELEVANCE)

    def _build_model_input(self, request: MetricRequest) -> dict:
        return {"text": request.system_prompt, "text_pair": request.user_query}

    def _build_llm_input(self, request: MetricRequest) -> dict:
        return {
            "user_query": request.user_query,
            "system_prompt": request.system_prompt,
        }


class ResponseRelevanceScorer(BaseRelevanceScorer):
    """Scorer for evaluating response relevance against system prompt and user query"""

    def __init__(self):
        super().__init__(MetricType.RESPONSE_RELEVANCE)

    def _build_model_input(self, request: MetricRequest) -> dict:
        return {
            "text": f"System Prompt: {request.system_prompt} \n User Query: {request.user_query}",
            "text_pair": request.response,
        }

    def _build_llm_input(self, request: MetricRequest) -> dict:
        return {
            "user_query": request.user_query,
            "system_prompt": request.system_prompt,
            "response": request.response,
        }
