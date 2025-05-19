import abc
from typing import Any, Callable

from schemas.metric_schemas import MetricRequest, MetricScore
from schemas.scorer_schemas import RuleScore, ScoreRequest


def validate_request_decorator(func: Callable[[ScoreRequest], Any]):
    def validate_request(request: ScoreRequest):
        """Valids to make sure the request is valid"""
        if not request.user_prompt and not request.llm_response:
            raise ValueError("Must provide either user prompt or llm response")

        return func(request)

    return validate_request


class RuleScorer(abc.ABC):
    @abc.abstractmethod
    @validate_request_decorator
    def score(self, request: ScoreRequest) -> RuleScore:
        pass


class MetricScorer(abc.ABC):
    @abc.abstractmethod
    @validate_request_decorator
    def score(self, request: MetricRequest) -> MetricScore:
        pass
