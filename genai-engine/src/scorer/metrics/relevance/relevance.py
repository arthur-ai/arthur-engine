import logging
from abc import ABC, abstractmethod
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
    """
    Rounds a score to consistent precision for all relevance metrics.
    Single source of truth for score rounding precision.
    """
    return round(float(score), 2)


# Schemas to force JSON output to the right format
class QueryRelevanceResponseSchema(BaseModel):
    relevance_score: float = Field(
        description="A numerical value where 1 means 'highly relevant' and 0 means 'completely irrelevant'",
    )
    justification: str = Field(
        description="Explanation of why the query is relevant or not",
    )
    suggested_refinement: str = Field(
        description="If the query is somewhat relevant but not fully aligned, suggest a better phrasing. 'None' if not applicable",
    )


class ResponseRelevanceResponseSchema(BaseModel):
    relevance_score: float = Field(
        description="A numerical value where 1 means 'highly relevant' and 0 means 'completely irrelevant'",
    )
    justification: str = Field(
        description="Explanation of why the response is relevant or not",
    )
    suggested_refinement: str = Field(
        description="If the response is somewhat relevant but not fully aligned, suggest a better phrasing. 'None' if not applicable",
    )


def get_model(temperature: float = 0.0):
    return get_llm_executor().get_gpt_model(chat_temperature=temperature)


def get_query_relevance_chain_structured(temperature: float = 0.0):
    """Structured output chain for query relevance"""
    model = get_model(temperature)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query"],
        template=USER_QUERY_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model.with_structured_output(QueryRelevanceResponseSchema)
    return evaluation_chain


def get_query_relevance_chain_legacy(temperature: float = 0.0):
    """Legacy chain for query relevance with JSON parser"""
    model = get_model(temperature)

    parser = JsonOutputParser(pydantic_object=QueryRelevanceResponseSchema)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
        },
        template=USER_QUERY_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model | parser
    return evaluation_chain


def get_response_relevance_chain_structured(temperature: float = 0.0):
    """Structured output chain for response relevance"""
    model = get_model(temperature)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "response"],
        template=RESPONSE_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model.with_structured_output(
        ResponseRelevanceResponseSchema,
    )
    return evaluation_chain


def get_response_relevance_chain_legacy(temperature: float = 0.0):
    """Legacy chain for response relevance with JSON parser"""
    model = get_model(temperature)

    parser = JsonOutputParser(pydantic_object=ResponseRelevanceResponseSchema)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "response"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
        },
        template=RESPONSE_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE,
    )

    evaluation_chain = pt | model | parser
    return evaluation_chain


# Legacy functions for backward compatibility
def get_query_relevance_chain(temperature: float = 0.0):
    """Legacy function - uses structured outputs if supported, falls back to legacy"""
    if get_llm_executor().supports_structured_outputs():
        return get_query_relevance_chain_structured(temperature)
    else:
        return get_query_relevance_chain_legacy(temperature)


def get_response_relevance_chain(temperature: float = 0.0):
    """Legacy function - uses structured outputs if supported, falls back to legacy"""
    if get_llm_executor().supports_structured_outputs():
        return get_response_relevance_chain_structured(temperature)
    else:
        return get_response_relevance_chain_legacy(temperature)


class BaseRelevanceScorer(MetricScorer):
    """Base class for relevance scorers with common functionality"""

    def __init__(self, metric_type: MetricType):
        super().__init__()
        self.metric_type = metric_type
        self.relevance_reranker = get_relevance_reranker()
        self.bert_scorer = BertScorer(metric_type)

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

        if relevance_models_enabled() and self.relevance_reranker is not None:
            # Get reranker score
            reranker_input = self._build_reranker_input(request)
            res = self.relevance_reranker(reranker_input)
            reranker_score = res["score"]

            # Get BERT score
            metric_score = (
                self.bert_scorer.score_query(request)
                if self.metric_type == MetricType.QUERY_RELEVANCE
                else self.bert_scorer.score_response(request)
            )
            bert_f_score = (
                metric_score.details.query_relevance.bert_f_score
                if self.metric_type == MetricType.QUERY_RELEVANCE
                else metric_score.details.response_relevance.bert_f_score
            )

        return bert_f_score, reranker_score

    def _get_llm_scores(
        self,
        request: MetricRequest,
    ) -> Tuple[float, str, str, int, int]:
        """Get scores from LLM judge"""
        relevance_chain = self._get_relevance_chain()
        chain_call = lambda: relevance_chain.invoke(self._build_llm_input(request))

        try:
            llm_judge_response, token_consumption = self.prompt_llm(
                chain_call,
                f"{self.metric_type.value} Check",
            )
        except Exception as e:
            # Return default values when LLM fails
            return None, None, None, 0, 0

        # Handle both structured output (Pydantic model) and legacy (dict) responses
        if isinstance(
            llm_judge_response,
            (QueryRelevanceResponseSchema, ResponseRelevanceResponseSchema),
        ):
            # Structured output - use attribute access
            relevance_score_llm = llm_judge_response.relevance_score
            justification = llm_judge_response.justification
            suggested_refinement = llm_judge_response.suggested_refinement
        else:
            # Legacy output - use dictionary access
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

    def _create_metric_result(
        self,
        metric_details: MetricScoreDetails,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> MetricResult:
        """Create a MetricResult from the metric details"""
        return MetricResult(
            id="",  # This will be set by the calling code
            metric_type=self.metric_type,
            details=metric_details,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=0,  # This will be set by the calling code
        )

    def _get_relevance_chain(self):
        """Get the appropriate relevance chain based on structured output support"""
        raise NotImplementedError("Subclasses must implement this method")

    def _build_reranker_input(self, request: MetricRequest) -> dict:
        """Build input for the reranker model"""
        raise NotImplementedError("Subclasses must implement this method")

    def _build_llm_input(self, request: MetricRequest) -> dict:
        """Build input for the LLM judge"""
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def prompt_llm(f, operation_name: str):
        return get_llm_executor().execute(f, operation_name)


class UserQueryRelevanceScorer(BaseRelevanceScorer):
    """Scorer for evaluating user query relevance against system prompt"""

    def __init__(self):
        super().__init__(MetricType.QUERY_RELEVANCE)

    def _get_relevance_chain(self):
        """Get the appropriate relevance chain based on structured output support"""
        if get_llm_executor().supports_structured_outputs():
            return get_query_relevance_chain_structured()
        else:
            return get_query_relevance_chain_legacy()

    def _build_reranker_input(self, request: MetricRequest) -> dict:
        """Build input for the reranker model"""
        return {"text": request.system_prompt, "text_pair": request.user_query}

    def _build_llm_input(self, request: MetricRequest) -> dict:
        """Build input for the LLM judge"""
        return {
            "user_query": request.user_query,
            "system_prompt": request.system_prompt,
        }

    def score(self, request: MetricRequest, config: dict) -> MetricResult:
        """Scores user's query against system prompt for relevance"""
        use_llm_judge = config.get("use_llm_judge", True)

        # If both LLM judge is disabled and models are disabled, return defaults
        if self._should_return_defaults(use_llm_judge):
            metric_details = MetricScoreDetails(
                query_relevance=QueryRelevanceMetric(
                    bert_f_score=None,
                    reranker_relevance_score=None,
                    llm_relevance_score=None,
                    reason=None,
                    refinement=None,
                ),
            )
            return self._create_metric_result(metric_details)

        # Get model scores
        bert_f_score, reranker_score = self._get_model_scores(request)

        # Create metric details
        metric_details = MetricScoreDetails(
            query_relevance=QueryRelevanceMetric(
                bert_f_score=(
                    round_score(bert_f_score) if bert_f_score is not None else None
                ),
                reranker_relevance_score=(
                    round_score(reranker_score) if reranker_score is not None else None
                ),
                llm_relevance_score=None,
                reason=None,
                refinement=None,
            ),
        )

        # Get LLM scores if requested
        if use_llm_judge:
            llm_score, reason, refinement, prompt_tokens, completion_tokens = (
                self._get_llm_scores(request)
            )
            metric_details.query_relevance.llm_relevance_score = (
                round_score(llm_score) if llm_score is not None else None
            )
            metric_details.query_relevance.reason = reason
            metric_details.query_relevance.refinement = refinement

            logger.info(
                f"User Query Relevance Result: {llm_score}, {reranker_score}, {bert_f_score}",
            )
            return self._create_metric_result(
                metric_details,
                prompt_tokens,
                completion_tokens,
            )
        else:
            logger.info(
                f"User Query Relevance Result: {reranker_score}, {bert_f_score}",
            )
            return self._create_metric_result(metric_details)


class ResponseRelevanceScorer(BaseRelevanceScorer):
    """Scorer for evaluating response relevance against system prompt and user query"""

    def __init__(self):
        super().__init__(MetricType.RESPONSE_RELEVANCE)

    def _get_relevance_chain(self):
        """Get the appropriate relevance chain based on structured output support"""
        if get_llm_executor().supports_structured_outputs():
            return get_response_relevance_chain_structured()
        else:
            return get_response_relevance_chain_legacy()

    def _build_reranker_input(self, request: MetricRequest) -> dict:
        """Build input for the reranker model"""
        return {
            "text": f"System Prompt: {request.system_prompt} \n User Query: {request.user_query}",
            "text_pair": request.response,
        }

    def _build_llm_input(self, request: MetricRequest) -> dict:
        """Build input for the LLM judge"""
        return {
            "user_query": request.user_query,
            "system_prompt": request.system_prompt,
            "response": request.response,
        }

    def score(self, request: MetricRequest, config: dict) -> MetricResult:
        """Scores response against system prompt and user query for relevance"""
        use_llm_judge = config.get("use_llm_judge", True)

        # If both LLM judge is disabled and models are disabled, return defaults
        if self._should_return_defaults(use_llm_judge):
            metric_details = MetricScoreDetails(
                response_relevance=ResponseRelevanceMetric(
                    bert_f_score=None,
                    reranker_relevance_score=None,
                    llm_relevance_score=None,
                    reason=None,
                    refinement=None,
                ),
            )
            return self._create_metric_result(metric_details)

        # Get model scores
        bert_f_score, reranker_score = self._get_model_scores(request)

        # Create metric details
        metric_details = MetricScoreDetails(
            response_relevance=ResponseRelevanceMetric(
                bert_f_score=(
                    round_score(bert_f_score) if bert_f_score is not None else None
                ),
                reranker_relevance_score=(
                    round_score(reranker_score) if reranker_score is not None else None
                ),
                llm_relevance_score=None,
                reason=None,
                refinement=None,
            ),
        )

        # Get LLM scores if requested
        if use_llm_judge:
            llm_score, reason, refinement, prompt_tokens, completion_tokens = (
                self._get_llm_scores(request)
            )
            metric_details.response_relevance.llm_relevance_score = (
                round_score(llm_score) if llm_score is not None else None
            )
            metric_details.response_relevance.reason = reason
            metric_details.response_relevance.refinement = refinement

            logger.info(
                f"Response Relevance Result: {llm_score}, {reranker_score}, {bert_f_score}",
            )
            return self._create_metric_result(
                metric_details,
                prompt_tokens,
                completion_tokens,
            )
        else:
            logger.info(f"Response Relevance Result: {reranker_score}, {bert_f_score}")
            return self._create_metric_result(metric_details)


class BertRelevanceScorer(MetricScorer, ABC):
    """Abstract base class for BERT-based relevance scoring"""

    def __init__(self):
        self.model = get_bert_scorer()

    @abstractmethod
    def create_metric_details(self, f_scores) -> MetricScoreDetails:
        pass

    @abstractmethod
    def get_metric_type(self) -> MetricType:
        pass

    def score(
        self,
        candidate_batch: list[str],
        ground_truth_batch: list[str],
    ) -> MetricResult:
        """
        Scores the candidate batch against the system batch using the BERTScorer.
        """
        candidate_batch_scores = self.model.score(
            candidate_batch,
            ground_truth_batch,
            verbose=False,
        )
        p, r, f = candidate_batch_scores

        # Calculate the average F1 score (should always be 1 value)
        f_scores = f.mean(dim=0)

        return MetricResult(
            id="",  # This will be set by the calling code
            metric_type=self.get_metric_type(),
            details=self.create_metric_details(f_scores),
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,  # This will be set by the calling code
        )


class BertScorer(BertRelevanceScorer):
    """BERT scorer that can handle both query and response relevance"""

    def __init__(self, metric_type: MetricType):
        super().__init__()
        self.metric_type = metric_type

    def create_metric_details(self, f_scores) -> MetricScoreDetails:
        if self.metric_type == MetricType.QUERY_RELEVANCE:
            return MetricScoreDetails(
                query_relevance=QueryRelevanceMetric(
                    bert_f_score=round_score(f_scores),
                    reranker_relevance_score=None,  # Not used in BERT-only scoring
                    llm_relevance_score=None,
                    reason=None,
                    refinement=None,
                ),
            )
        else:  # RESPONSE_RELEVANCE
            return MetricScoreDetails(
                response_relevance=ResponseRelevanceMetric(
                    bert_f_score=round_score(f_scores),
                    reranker_relevance_score=None,  # Not used in BERT-only scoring
                    llm_relevance_score=None,
                    reason=None,
                    refinement=None,
                ),
            )

    def get_metric_type(self) -> MetricType:
        return self.metric_type

    def score_query(self, request: MetricRequest) -> MetricResult:
        """Score query relevance"""
        # Check if BERT scorer is available
        if self.model is None:
            # Return default result when BERT scorer is disabled
            return MetricResult(
                id="",
                metric_type=self.metric_type,
                details=self.create_metric_details(0.0),  # Default score
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
            )

        candidate_batch = [request.user_query]
        ground_truth_batch = [request.system_prompt]
        return super().score(candidate_batch, ground_truth_batch)

    def score_response(self, request: MetricRequest) -> MetricResult:
        """Score response relevance"""
        # Check if BERT scorer is available
        if self.model is None:
            # Return default result when BERT scorer is disabled
            return MetricResult(
                id="",
                metric_type=self.metric_type,
                details=self.create_metric_details(0.0),  # Default score
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
            )

        candidate_batch = [request.response]
        ground_truth_batch = [request.system_prompt]
        return super().score(candidate_batch, ground_truth_batch)
