"""V2 ML scorer wrappers.

Each class wraps a V1 scorer and translates V1 types (ScoreRequest, RuleScore,
RuleResultEnum) to V2 types (MLScoreResult). No V1 types are exposed to callers.
"""

from typing import Any

from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.scorer_schemas import ScoreRequest
from scorer.base_ml_scorer import BaseMLScorer, MLScoreResult


class PIIScorerV2(BaseMLScorer):
    """Wraps BinaryPIIDataClassifier (GLiNER + Presidio, V2)."""

    def __init__(self) -> None:
        # Deferred import: scorer modules load heavyweight ML models (GLiNER, Presidio,
        # Transformers) on import. Keeping these inside __init__ ensures models are only
        # loaded when the scorer is first instantiated, not at server startup.
        from scorer.checks.pii.classifier import BinaryPIIDataClassifier

        self._inner = BinaryPIIDataClassifier()

    def score(self, text: str, config: dict[str, Any]) -> MLScoreResult:
        request = ScoreRequest(
            rule_type=RuleType.PII_DATA,
            scoring_text=text,
            disabled_pii_entities=config.get("disabled_pii_entities"),
            pii_confidence_threshold=config.get("pii_confidence_threshold"),
            allow_list=config.get("allow_list"),
        )
        rule_score = self._inner.score(request)
        passed = rule_score.result == RuleResultEnum.PASS
        reason = (rule_score.details.message or "") if rule_score.details else ""
        if not reason:
            reason = "No PII detected." if passed else "PII detected."
        return MLScoreResult(passed=passed, reason=reason)


class PIIScorerV1(BaseMLScorer):
    """Wraps BinaryPIIDataClassifierV1 (Presidio only)."""

    def __init__(self) -> None:
        from scorer.checks.pii.classifier_v1 import BinaryPIIDataClassifierV1

        self._inner = BinaryPIIDataClassifierV1()

    def score(self, text: str, config: dict[str, Any]) -> MLScoreResult:
        request = ScoreRequest(
            rule_type=RuleType.PII_DATA,
            scoring_text=text,
            disabled_pii_entities=config.get("disabled_pii_entities"),
            pii_confidence_threshold=config.get("pii_confidence_threshold"),
            allow_list=config.get("allow_list"),
        )
        rule_score = self._inner.score(request)
        passed = rule_score.result == RuleResultEnum.PASS
        reason = (rule_score.details.message or "") if rule_score.details else ""
        if not reason:
            reason = "No PII detected." if passed else "PII detected."
        return MLScoreResult(passed=passed, reason=reason)


class ToxicityMLScorer(BaseMLScorer):
    """Wraps ToxicityScorer."""

    def __init__(self) -> None:
        from scorer.checks.toxicity.toxicity import ToxicityScorer
        from utils.model_load import TOXICITY_MODEL, TOXICITY_TOKENIZER

        self._inner = ToxicityScorer(
            toxicity_model=TOXICITY_MODEL,
            toxicity_tokenizer=TOXICITY_TOKENIZER,
            harmful_request_model=None,
            harmful_request_tokenizer=None,
        )

    def score(self, text: str, config: dict[str, Any]) -> MLScoreResult:
        request = ScoreRequest(
            rule_type=RuleType.TOXICITY,
            scoring_text=text,
            user_prompt=text,
            toxicity_threshold=config.get("toxicity_threshold"),
        )
        rule_score = self._inner.score(request)
        passed = rule_score.result == RuleResultEnum.PASS
        reason = (rule_score.details.message or "") if rule_score.details else ""
        if not reason:
            reason = "No toxicity detected." if passed else "Toxic content detected."
        return MLScoreResult(passed=passed, reason=reason)


class PromptInjectionMLScorer(BaseMLScorer):
    """Wraps BinaryPromptInjectionClassifier."""

    def __init__(self) -> None:
        from scorer.checks.prompt_injection.classifier import (
            BinaryPromptInjectionClassifier,
        )
        from utils.model_load import PROMPT_INJECTION_MODEL, PROMPT_INJECTION_TOKENIZER

        self._inner = BinaryPromptInjectionClassifier(
            model=PROMPT_INJECTION_MODEL,
            tokenizer=PROMPT_INJECTION_TOKENIZER,
        )

    def score(self, text: str, config: dict[str, Any]) -> MLScoreResult:
        request = ScoreRequest(
            rule_type=RuleType.PROMPT_INJECTION,
            user_prompt=text,
        )
        rule_score = self._inner.score(request)
        passed = rule_score.result == RuleResultEnum.PASS
        reason = (rule_score.details.message or "") if rule_score.details else ""
        if not reason:
            reason = (
                "No prompt injection detected."
                if passed
                else "Prompt injection detected."
            )
        return MLScoreResult(passed=passed, reason=reason)
