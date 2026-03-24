"""Rule-based continuous eval evaluator.

Wraps the existing ScorerClient / RuleEngine for PII_DATA, PROMPT_INJECTION, and
TOXICITY rule types so they can run as CE evaluators inside
ContinuousEvalQueueService.
"""

import uuid
from datetime import datetime
from typing import Optional

from arthur_common.models.common_schemas import PIIConfig, ToxicityConfig
from arthur_common.models.enums import RuleResultEnum, RuleScope, RuleType

from rules_engine import RuleEngine
from schemas.enums import RuleDataType, RuleScoringMethod
from schemas.internal_schemas import Rule, ValidationRequest
from schemas.rules_schema_utils import RuleData
from schemas.scorer_schemas import RuleScore
from scorer.score import ScorerClient
from utils import constants

# Rule types supported by the CE rule evaluator (Phase 1)
SUPPORTED_RULE_TYPES = {RuleType.PII_DATA, RuleType.PROMPT_INJECTION, RuleType.TOXICITY}


class RuleCEEvaluator:
    """Evaluates rule-based continuous evals against extracted trace text.

    Each call to evaluate() constructs a transient Rule from the stored
    rule_type + rule_config and runs it through the shared RuleEngine.
    """

    def __init__(self, scorer_client: ScorerClient) -> None:
        self._scorer_client = scorer_client

    def evaluate(
        self,
        rule_type: RuleType,
        rule_config: Optional[dict],
        validation_request: ValidationRequest,
    ) -> RuleScore:
        """Run a rule against a validation request.

        Args:
            rule_type: One of the supported Phase-1 rule types.
            rule_config: Optional JSON config blob stored on the CE row.
            validation_request: Prompt/response text extracted from the trace.

        Returns:
            RuleScore with result (PASS/FAIL/SKIPPED/UNAVAILABLE) and details.
        """
        if rule_type not in SUPPORTED_RULE_TYPES:
            raise ValueError(
                f"Unsupported rule type for CE evaluator: {rule_type}. "
                f"Supported: {', '.join(r.value for r in SUPPORTED_RULE_TYPES)}"
            )

        rule = self._build_rule(rule_type, rule_config or {})
        rule_engine = RuleEngine(self._scorer_client)
        result = rule_engine.run_rule(validation_request, rule)
        return result.rule_score_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_rule(self, rule_type: RuleType, config: dict) -> Rule:
        """Construct a transient Rule object from stored config."""
        rule_data = self._build_rule_data(rule_type, config)
        return Rule(
            id=str(uuid.uuid4()),
            name=f"ce_{rule_type.value}",
            type=rule_type,
            prompt_enabled=True,
            response_enabled=True,
            scoring_method=RuleScoringMethod.BINARY,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            rule_data=rule_data,
            scope=RuleScope.TASK,
            archived=False,
        )

    def _build_rule_data(self, rule_type: RuleType, config: dict) -> list[RuleData]:
        """Build RuleData entries from a stored config dict."""
        if rule_type == RuleType.PII_DATA:
            return self._build_pii_rule_data(config)
        elif rule_type == RuleType.TOXICITY:
            return self._build_toxicity_rule_data(config)
        elif rule_type == RuleType.PROMPT_INJECTION:
            return []
        raise ValueError(f"Unsupported rule type: {rule_type}")

    @staticmethod
    def _build_pii_rule_data(config: dict) -> list[RuleData]:
        rule_data: list[RuleData] = []
        if "disabled_pii_entities" in config and config["disabled_pii_entities"]:
            rule_data.append(
                RuleData(
                    id=str(uuid.uuid4()),
                    data_type=RuleDataType.PII_DISABLED_PII,
                    data=",".join(config["disabled_pii_entities"]),
                )
            )
        if "confidence_threshold" in config:
            rule_data.append(
                RuleData(
                    id=str(uuid.uuid4()),
                    data_type=RuleDataType.PII_THRESHOLD,
                    data=str(config["confidence_threshold"]),
                )
            )
        if "allow_list" in config and config["allow_list"]:
            rule_data.append(
                RuleData(
                    id=str(uuid.uuid4()),
                    data_type=RuleDataType.PII_ALLOW_LIST,
                    data=",".join(config["allow_list"]),
                )
            )
        return rule_data

    @staticmethod
    def _build_toxicity_rule_data(config: dict) -> list[RuleData]:
        threshold = config.get(
            "threshold", constants.DEFAULT_TOXICITY_RULE_THRESHOLD
        )
        return [
            RuleData(
                id=str(uuid.uuid4()),
                data_type=RuleDataType.TOXICITY_THRESHOLD,
                data=str(threshold),
            )
        ]
