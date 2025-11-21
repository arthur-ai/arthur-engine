import json
from typing import Dict, Protocol, Union, overload

from arthur_common.models.enums import MetricType, RuleType
from arthur_common.models.metric_schemas import MetricRequest

from schemas.internal_schemas import Metric, MetricResult
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import MetricScorer, RuleScorer


class ScorerMapping(Protocol):
    """Protocol for type-safe scorer mapping where RuleType -> RuleScorer and MetricType -> MetricScorer"""

    @overload
    def __getitem__(self, key: RuleType) -> RuleScorer: ...

    @overload
    def __getitem__(self, key: MetricType) -> MetricScorer: ...

    def __getitem__(
        self,
        key: Union[RuleType, MetricType],
    ) -> Union[RuleScorer, MetricScorer]: ...


class ScorerClient:
    def __init__(
        self,
        name_version_mapping: Dict[
            Union[RuleType, MetricType],
            Union[RuleScorer, MetricScorer],
        ],
    ):
        self.NAME_VERSION_MAPPING: ScorerMapping = name_version_mapping  # type: ignore[assignment]

    def score(self, score_request: ScoreRequest) -> RuleScore:
        """Scores any request with the provided rule

        :param score_request: scoring request object
        Returns: rule score
        """
        try:
            scorer_obj = self.NAME_VERSION_MAPPING[score_request.rule_type]
        except KeyError:
            raise ValueError(
                f"Rule type {score_request.rule_type} does not have a scorer",
            )

        return scorer_obj.score(score_request)

    def score_metric(
        self,
        metric_request: MetricRequest,
        metric: Metric,
    ) -> MetricResult:
        """Scores any request with the provided metric

        :param metric_request: metric request object
        :param metric_type: type of metric to score
        Returns: metric score
        """
        try:
            scorer_obj = self.NAME_VERSION_MAPPING[metric.type]
        except KeyError:
            raise ValueError(
                f"Metric type {metric.type} does not have a scorer",
            )
        config = json.loads(metric.config) if metric.config else {}

        result = scorer_obj.score(metric_request, config)

        return result
