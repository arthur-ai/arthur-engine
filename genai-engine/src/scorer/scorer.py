import abc
from typing import TYPE_CHECKING, Any, cast

from arthur_common.models.enums import RuleResultEnum
from arthur_common.models.metric_schemas import MetricRequest

from custom_types import FunctionT
from schemas.internal_schemas import MetricResult
from schemas.scorer_schemas import RuleScore, ScoreRequest

if TYPE_CHECKING:
    from services.model_warmup_service import ModelKey


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


def model_not_available_score(key: "ModelKey", message: str) -> RuleScore:
    """Build a ``MODEL_NOT_AVAILABLE`` ``RuleScore`` and nudge warmup.

    Several model-backed scorers need to short-circuit identically when their
    model isn't ready. Centralizing the shape here keeps the warmup-nudge +
    throttled-warning + zero-token ``RuleScore`` consistent across scorers.
    Exposed as a free function so non-``RuleScorer`` classes (e.g. the PII
    classifier) can use it too.
    """
    # Local import to avoid pulling the services package into this module's
    # import graph; the helper is opt-in for callers.
    from services.model_warmup_service import get_model_warmup_service

    warmup = get_model_warmup_service()
    warmup.ensure_warmup_started()
    warmup.warn_throttled(key, message)
    return RuleScore(
        result=RuleResultEnum.MODEL_NOT_AVAILABLE,
        prompt_tokens=0,
        completion_tokens=0,
    )


class RuleScorer(abc.ABC):
    @abc.abstractmethod
    @validate_request_decorator
    def score(self, request: ScoreRequest) -> RuleScore:
        pass

    def _model_not_available(self, key: "ModelKey", message: str) -> RuleScore:
        """Convenience wrapper around :func:`model_not_available_score`."""
        return model_not_available_score(key, message)


class MetricScorer(abc.ABC):
    @abc.abstractmethod
    @validate_request_decorator
    def score(self, request: MetricRequest, config: dict[str, Any]) -> MetricResult:
        pass
