import abc
from typing import Any, cast

from arthur_common.models.metric_schemas import MetricRequest

from custom_types import FunctionT
from schemas.internal_schemas import MetricResult
from schemas.scorer_schemas import RuleScore, ScoreRequest


def validate_request_decorator(func: FunctionT) -> FunctionT:
    def validate_request(
        self: Any,
        request: ScoreRequest | MetricRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Valids to make sure the request is valid"""
        # Only validate ScoreRequest (RuleScorer), MetricRequest has different fields
        if isinstance(request, ScoreRequest):
            if not request.user_prompt and not request.llm_response:
                raise ValueError("Must provide either user prompt or llm response")

        return func(self, request, *args, **kwargs)

    return cast(FunctionT, validate_request)


class RuleScorer(abc.ABC):
    @abc.abstractmethod
    @validate_request_decorator
    def score(self, request: ScoreRequest) -> RuleScore:
        pass


class MetricScorer(abc.ABC):
    @abc.abstractmethod
    @validate_request_decorator
    def score(self, request: MetricRequest, config: dict[str, Any]) -> MetricResult:
        pass
