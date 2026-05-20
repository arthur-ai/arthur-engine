"""Concrete ML scorer implementations and registry."""

from typing import Any, Dict, Optional

from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.enums import EvalType
from schemas.response_schemas import EvalRunResponse
from schemas.scorer_schemas import ScoreRequest
from scorer.base_ml_scorer import BaseMLScorer

ML_EVAL_TYPES = [
    EvalType.PII,
    EvalType.PII_V1,
    EvalType.TOXICITY,
    EvalType.PROMPT_INJECTION,
]

ML_EVAL_INPUT_VARIABLE = "input"

_SCORER_REGISTRY: Dict[str, BaseMLScorer] = {}


def _score_to_response(rule_score: Any) -> EvalRunResponse:
    passed = rule_score.result == RuleResultEnum.PASS
    reason = (rule_score.details.message or "") if rule_score.details else ""
    if not reason:
        reason = "No issues detected." if passed else "Issues detected."
    return EvalRunResponse(reason=reason, score=int(passed), cost="")


class PIIScorerV2(BaseMLScorer):
    def __init__(self, scorer: Any) -> None:
        self._scorer = scorer

    def run(self, text: str, config: Dict[str, Any]) -> EvalRunResponse:
        request = ScoreRequest(
            rule_type=RuleType.PII_DATA,
            scoring_text=text,
            disabled_pii_entities=config.get("disabled_pii_entities"),
            pii_confidence_threshold=config.get("pii_confidence_threshold"),
            allow_list=config.get("allow_list"),
        )
        return _score_to_response(self._scorer.score(request))


class PIIScorerV1(BaseMLScorer):
    def __init__(self, scorer: Any) -> None:
        self._scorer = scorer

    def run(self, text: str, config: Dict[str, Any]) -> EvalRunResponse:
        request = ScoreRequest(
            rule_type=RuleType.PII_DATA,
            scoring_text=text,
            disabled_pii_entities=config.get("disabled_pii_entities"),
            pii_confidence_threshold=config.get("pii_confidence_threshold"),
            allow_list=config.get("allow_list"),
        )
        return _score_to_response(self._scorer.score(request))


class ToxicityMLScorer(BaseMLScorer):
    def __init__(self, scorer: Any) -> None:
        self._scorer = scorer

    def run(self, text: str, config: Dict[str, Any]) -> EvalRunResponse:
        request = ScoreRequest(
            rule_type=RuleType.TOXICITY,
            scoring_text=text,
            user_prompt=text,
            toxicity_threshold=config.get("toxicity_threshold"),
        )
        return _score_to_response(self._scorer.score(request))


class PromptInjectionMLScorer(BaseMLScorer):
    def __init__(self, scorer: Any) -> None:
        self._scorer = scorer

    def run(self, text: str, config: Dict[str, Any]) -> EvalRunResponse:
        request = ScoreRequest(
            rule_type=RuleType.PROMPT_INJECTION,
            user_prompt=text,
        )
        return _score_to_response(self._scorer.score(request))


def get_ml_scorer(eval_type: str) -> Optional[BaseMLScorer]:
    """Return a cached BaseMLScorer for the given eval_type, or None if unknown."""
    if eval_type not in [e.value for e in ML_EVAL_TYPES]:
        return None
    if eval_type not in _SCORER_REGISTRY:
        if eval_type == EvalType.PII.value:
            from scorer.checks.pii.classifier import BinaryPIIDataClassifier

            _SCORER_REGISTRY[eval_type] = PIIScorerV2(BinaryPIIDataClassifier())
        elif eval_type == EvalType.PII_V1.value:
            from scorer.checks.pii.classifier_v1 import BinaryPIIDataClassifierV1

            _SCORER_REGISTRY[eval_type] = PIIScorerV1(BinaryPIIDataClassifierV1())
        elif eval_type == EvalType.TOXICITY.value:
            from scorer.checks.toxicity.toxicity import ToxicityScorer
            from utils.model_load import TOXICITY_MODEL, TOXICITY_TOKENIZER

            _SCORER_REGISTRY[eval_type] = ToxicityMLScorer(
                ToxicityScorer(
                    toxicity_model=TOXICITY_MODEL,
                    toxicity_tokenizer=TOXICITY_TOKENIZER,
                    harmful_request_model=None,
                    harmful_request_tokenizer=None,
                ),
            )
        elif eval_type == EvalType.PROMPT_INJECTION.value:
            from scorer.checks.prompt_injection.classifier import (
                BinaryPromptInjectionClassifier,
            )
            from utils.model_load import (
                PROMPT_INJECTION_MODEL,
                PROMPT_INJECTION_TOKENIZER,
            )

            _SCORER_REGISTRY[eval_type] = PromptInjectionMLScorer(
                BinaryPromptInjectionClassifier(
                    model=PROMPT_INJECTION_MODEL,
                    tokenizer=PROMPT_INJECTION_TOKENIZER,
                ),
            )
    return _SCORER_REGISTRY.get(eval_type)


def run_ml_scorer(eval_type: str, text: str, config: Dict[str, Any]) -> EvalRunResponse:
    """Run a cached ML scorer and return a unified EvalRunResponse."""
    scorer = get_ml_scorer(eval_type)
    if scorer is None:
        raise ValueError(
            f"No scorer registered for eval type '{eval_type}'. "
            f"Supported types: {[e.value for e in ML_EVAL_TYPES]}",
        )
    return scorer.run(text, config)
