"""Concrete ML scorer implementations."""

from typing import Any, Dict, Optional

from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.enums import EvalKind
from schemas.response_schemas import EvalRunResponse
from schemas.scorer_schemas import ScoreRequest
from scorer.base_ml_scorer import BaseMLScorer
from scorer.checks.pii.classifier import BinaryPIIDataClassifier
from scorer.checks.pii.classifier_v1 import BinaryPIIDataClassifierV1
from scorer.checks.prompt_injection.classifier import BinaryPromptInjectionClassifier
from scorer.checks.toxicity.toxicity import ToxicityScorer
from utils.model_load import (
    PROMPT_INJECTION_MODEL,
    PROMPT_INJECTION_TOKENIZER,
    TOXICITY_MODEL,
    TOXICITY_TOKENIZER,
)

ML_EVAL_INPUT_VARIABLE = "input"


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
    """Return a BaseMLScorer for the given eval_type, or None if unknown.

    Underlying models are cached by model_load.py; scorer wrappers are lightweight.
    """
    if eval_type == EvalKind.PII.value:
        return PIIScorerV2(BinaryPIIDataClassifier())
    elif eval_type == EvalKind.PII_V1.value:
        return PIIScorerV1(BinaryPIIDataClassifierV1())
    elif eval_type == EvalKind.TOXICITY.value:
        return ToxicityMLScorer(
            ToxicityScorer(
                toxicity_model=TOXICITY_MODEL,
                toxicity_tokenizer=TOXICITY_TOKENIZER,
                harmful_request_model=None,
                harmful_request_tokenizer=None,
            ),
        )
    elif eval_type == EvalKind.PROMPT_INJECTION.value:
        return PromptInjectionMLScorer(
            BinaryPromptInjectionClassifier(
                model=PROMPT_INJECTION_MODEL,
                tokenizer=PROMPT_INJECTION_TOKENIZER,
            ),
        )
    return None


def run_ml_scorer(eval_type: str, text: str, config: Dict[str, Any]) -> EvalRunResponse:
    """Run an ML scorer and return a unified EvalRunResponse."""
    scorer = get_ml_scorer(eval_type)
    if scorer is None:
        raise ValueError(f"No ML scorer registered for eval type '{eval_type}'.")
    return scorer.run(text, config)
