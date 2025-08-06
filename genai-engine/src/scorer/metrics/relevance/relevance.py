import logging
from abc import ABC, abstractmethod

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
from scorer.llm_client import get_llm_executor, handle_llm_exception
from scorer.metrics.relevance.prompt_templates import (
    RESPONSE_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE,
    RESPONSE_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE,
    USER_QUERY_RELEVANCE_NON_STRUCTURED_PROMPT_TEMPLATE,
    USER_QUERY_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE,
)
from scorer.scorer import MetricScorer
from utils.model_load import get_bert_scorer, get_relevance_reranker

logger = logging.getLogger()


def round_score(score) -> float:
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


def get_model(temperature=0.0):
    return get_llm_executor().get_gpt_model(chat_temperature=temperature)


def get_query_relevance_chain_structured(temperature=0.0):
    """Structured output chain for query relevance"""
    model = get_model(temperature)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query"],
        template=USER_QUERY_RELEVANCE_STRUCTURED_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model.with_structured_output(QueryRelevanceResponseSchema)
    return evaluation_chain


def get_query_relevance_chain_legacy(temperature=0.0):
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


def get_response_relevance_chain_structured(temperature=0.0):
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


def get_response_relevance_chain_legacy(temperature=0.0):
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
def get_query_relevance_chain(temperature=0.0):
    """Legacy function - uses structured outputs if supported, falls back to legacy"""
    if get_llm_executor().supports_structured_outputs():
        return get_query_relevance_chain_structured(temperature)
    else:
        return get_query_relevance_chain_legacy(temperature)


def get_response_relevance_chain(temperature=0.0):
    """Legacy function - uses structured outputs if supported, falls back to legacy"""
    if get_llm_executor().supports_structured_outputs():
        return get_response_relevance_chain_structured(temperature)
    else:
        return get_response_relevance_chain_legacy(temperature)


class UserQueryRelevanceScorer(MetricScorer):
    def __init__(self):
        super().__init__()
        self.relevance_reranker = get_relevance_reranker()
        self.bert_scorer = UnifiedBertScorer(MetricType.QUERY_RELEVANCE)

    def _get_relevance_chain(self):
        """Get the appropriate relevance chain based on structured output support"""
        if get_llm_executor().supports_structured_outputs():
            return get_query_relevance_chain_structured()
        else:
            return get_query_relevance_chain_legacy()

    def score(self, request: MetricRequest, config: dict) -> MetricResult:
        """Scores user's query against system prompt for relevance"""
        use_llm_judge = config.get("use_llm_judge", True)
        query = request.user_query
        system_prompt = request.system_prompt
        # truncate the query and system prompt to 200 words
        # query = ' '.join(query.split()[:200])
        # system_prompt = ' '.join(system_prompt.split()[:200])

        relevance_pair = {"text": system_prompt, "text_pair": query}
        res = self.relevance_reranker(relevance_pair)
        relevance_score = res["score"]
        metric_score = self.bert_scorer.score_query(request)
        bert_f_score = metric_score.details.query_relevance.bert_f_score

        if use_llm_judge:
            relevance_chain = self._get_relevance_chain()
            chain_call = lambda: relevance_chain.invoke(
                {
                    "user_query": request.user_query,
                    "system_prompt": request.system_prompt,
                },
            )
            try:
                llm_judge_response, token_consumption = self.prompt_llm(
                    chain_call,
                    "User Query Relevance Check",
                )
            except Exception as e:
                return handle_llm_exception(e)

            # Handle both structured output (Pydantic model) and legacy (dict) responses
            if isinstance(llm_judge_response, QueryRelevanceResponseSchema):
                # Structured output - use attribute access
                relevance_score_llm = llm_judge_response.relevance_score
                justification = llm_judge_response.justification
                suggested_refinement = llm_judge_response.suggested_refinement
            else:
                # Legacy output - use dictionary access
                relevance_score_llm = llm_judge_response["relevance_score"]
                justification = llm_judge_response["justification"]
                suggested_refinement = llm_judge_response["suggested_refinement"]

            return MetricResult(
                id="",  # This will be set by the calling code
                metric_type=MetricType.QUERY_RELEVANCE,
                details=MetricScoreDetails(
                    query_relevance=QueryRelevanceMetric(
                        bert_f_score=round_score(bert_f_score),
                        reranker_relevance_score=round_score(relevance_score),
                        llm_relevance_score=round_score(relevance_score_llm),
                        reason=justification,
                        refinement=suggested_refinement,
                    ),
                ),
                prompt_tokens=token_consumption.prompt_tokens,
                completion_tokens=token_consumption.completion_tokens,
                latency_ms=0,  # This will be set by the calling code
            )
        else:
            return MetricResult(
                id="",  # This will be set by the calling code
                metric_type=MetricType.QUERY_RELEVANCE,
                details=MetricScoreDetails(
                    query_relevance=QueryRelevanceMetric(
                        bert_f_score=round_score(bert_f_score),
                        reranker_relevance_score=round_score(relevance_score),
                        llm_relevance_score=0,
                        reason=None,
                        refinement=None,
                    ),
                ),
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,  # This will be set by the calling code
            )

    @staticmethod
    def prompt_llm(f, operation_name: str):
        return get_llm_executor().execute(f, operation_name)


class ResponseRelevanceScorer(MetricScorer):
    def __init__(self):
        super().__init__()
        self.relevance_reranker = get_relevance_reranker()
        self.bert_scorer = UnifiedBertScorer(MetricType.RESPONSE_RELEVANCE)

    def _get_relevance_chain(self):
        """Get the appropriate relevance chain based on structured output support"""
        if get_llm_executor().supports_structured_outputs():
            return get_response_relevance_chain_structured()
        else:
            return get_response_relevance_chain_legacy()

    def score(self, request: MetricRequest, config: dict) -> MetricResult:
        """Scores user's query against system prompt for relevance"""
        use_llm_judge = config.get("use_llm_judge", True)
        query = request.user_query
        response = request.response
        system_prompt = request.system_prompt
        # TODO: truncation may be needed

        relevance_pair = {
            "text": f"System Prompt: {system_prompt} \n User Query: {query}",
            "text_pair": response,
        }
        res = self.relevance_reranker(relevance_pair)
        relevance_score = res["score"]

        metric_score = self.bert_scorer.score_response(request)
        bert_f_score = metric_score.details.response_relevance.bert_f_score

        if use_llm_judge:
            relevance_chain = self._get_relevance_chain()
            chain_call = lambda: relevance_chain.invoke(
                {
                    "user_query": request.user_query,
                    "system_prompt": request.system_prompt,
                    "response": response,
                },
            )
            try:
                llm_judge_response, token_consumption = self.prompt_llm(
                    chain_call,
                    "Response Relevance Check",
                )
            except Exception as e:
                return handle_llm_exception(e)

            # Handle both structured output (Pydantic model) and legacy (dict) responses
            if isinstance(llm_judge_response, ResponseRelevanceResponseSchema):
                # Structured output - use attribute access
                relevance_score_llm = llm_judge_response.relevance_score
                justification = llm_judge_response.justification
                suggested_refinement = llm_judge_response.suggested_refinement
            else:
                # Legacy output - use dictionary access
                relevance_score_llm = llm_judge_response["relevance_score"]
                justification = llm_judge_response["justification"]
                suggested_refinement = llm_judge_response["suggested_refinement"]

            return MetricResult(
                id="",  # This will be set by the calling code
                metric_type=MetricType.RESPONSE_RELEVANCE,
                details=MetricScoreDetails(
                    response_relevance=ResponseRelevanceMetric(
                        bert_f_score=round_score(bert_f_score),
                        reranker_relevance_score=round_score(relevance_score),
                        llm_relevance_score=round_score(relevance_score_llm),
                        reason=justification,
                        refinement=suggested_refinement,
                    ),
                ),
                prompt_tokens=token_consumption.prompt_tokens,
                completion_tokens=token_consumption.completion_tokens,
                latency_ms=0,  # This will be set by the calling code
            )
        else:
            return MetricResult(
                id="",  # This will be set by the calling code
                metric_type=MetricType.RESPONSE_RELEVANCE,
                details=MetricScoreDetails(
                    response_relevance=ResponseRelevanceMetric(
                        bert_f_score=round_score(bert_f_score),
                        reranker_relevance_score=round_score(relevance_score),
                        llm_relevance_score=0,
                        reason=None,
                        refinement=None,
                    ),
                ),
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,  # This will be set by the calling code
            )

    @staticmethod
    def prompt_llm(f, operation_name: str):
        return get_llm_executor().execute(f, operation_name)


class BertRelevanceScorer(MetricScorer, ABC):
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


class UnifiedBertScorer(BertRelevanceScorer):
    """Unified BERT scorer that can handle both query and response relevance"""

    def __init__(self, metric_type: MetricType):
        super().__init__()
        self.metric_type = metric_type

    def create_metric_details(self, f_scores) -> MetricScoreDetails:
        if self.metric_type == MetricType.QUERY_RELEVANCE:
            return MetricScoreDetails(
                query_relevance=QueryRelevanceMetric(
                    bert_f_score=round_score(f_scores),
                    reranker_relevance_score=0,
                    llm_relevance_score=None,
                    reason=None,
                    refinement=None,
                ),
            )
        else:  # RESPONSE_RELEVANCE
            return MetricScoreDetails(
                response_relevance=ResponseRelevanceMetric(
                    bert_f_score=round_score(f_scores),
                    reranker_relevance_score=0,
                    llm_relevance_score=None,
                    reason=None,
                    refinement=None,
                ),
            )

    def get_metric_type(self) -> MetricType:
        return self.metric_type

    def score_query(self, request: MetricRequest) -> MetricResult:
        """Score query relevance"""
        candidate_batch = [request.user_query]
        ground_truth_batch = [request.system_prompt]
        return super().score(candidate_batch, ground_truth_batch)

    def score_response(self, request: MetricRequest) -> MetricResult:
        """Score response relevance"""
        candidate_batch = [request.response]
        ground_truth_batch = [request.system_prompt]
        return super().score(candidate_batch, ground_truth_batch)
