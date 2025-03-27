from typing import Dict

from schemas.enums import RuleType
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import RuleScorer


class ScorerClient:
    def __init__(self, name_version_mapping: Dict[RuleType, RuleScorer]):
        self.NAME_VERSION_MAPPING: Dict[RuleType, RuleScorer] = name_version_mapping

    def score(self, score_request: ScoreRequest) -> RuleScore:
        """Scores any request with the provided rule

        :param score_request: scoring request object
        Returns: rule score
        """
        try:
            scorer_obj = self.NAME_VERSION_MAPPING[score_request.rule_type]
        except ValueError:
            raise ValueError(
                f"Rule type {score_request.rule_type} does not have a scorer",
            )

        return scorer_obj.score(score_request)
