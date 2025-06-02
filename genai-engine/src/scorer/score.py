from typing import Dict, Union
import json
from schemas.enums import RuleType, MetricType
from schemas.internal_schemas import Metric
from schemas.scorer_schemas import RuleScore, ScoreRequest
from schemas.metric_schemas import MetricScore, MetricRequest
from scorer.scorer import RuleScorer, MetricScorer


class ScorerClient:
    def __init__(self, name_version_mapping: Dict[Union[RuleType, MetricType], Union[RuleScorer, MetricScorer]]):
        self.NAME_VERSION_MAPPING: Dict[Union[RuleType, MetricType], Union[RuleScorer, MetricScorer]] = name_version_mapping

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

    def score_metric(self, metric_request: MetricRequest, metric: Metric) -> MetricScore:
        """Scores any request with the provided metric

        :param metric_request: metric request object
        :param metric_type: type of metric to score
        Returns: metric score
        """
        try:
            scorer_obj = self.NAME_VERSION_MAPPING[metric.metric_type]
        except KeyError:
            raise ValueError(
                f"Metric type {metric.metric_type} does not have a scorer",
            )
        config = json.loads(metric.metric_config) if metric.metric_config else {}
        return scorer_obj.score(metric_request, config)
