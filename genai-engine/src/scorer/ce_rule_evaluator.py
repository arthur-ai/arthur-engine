"""CE Rule Evaluator for running guardrail rules in the continuous eval pipeline."""

import json
import logging
from typing import Optional

from arthur_common.models.enums import RuleResultEnum, RuleType
from pydantic import BaseModel

from schemas.internal_schemas import Span
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.checks.pii.classifier import BinaryPIIDataClassifier
from scorer.checks.prompt_injection.classifier import BinaryPromptInjectionClassifier
from scorer.checks.toxicity.toxicity import ToxicityScorer

logger = logging.getLogger(__name__)


class CEEvaluationResult(BaseModel):
    """Result of a continuous eval rule evaluation."""

    annotation_score: int  # 1 = pass, 0 = fail
    annotation_description: str  # JSON-serialized rule detail


class RuleCEEvaluator:
    """
    Evaluates guardrail rules (PII_DATA, PROMPT_INJECTION, TOXICITY) on spans
    for use in the continuous eval pipeline.

    Targeting is implicit per rule type:
    - PROMPT_INJECTION: input only
    - TOXICITY: output only
    - PII_DATA: both input and output

    Results are purely observational (no blocking).
    """

    def __init__(self) -> None:
        self.pii_classifier = BinaryPIIDataClassifier()
        self.prompt_injection_classifier = BinaryPromptInjectionClassifier(
            model=None,
            tokenizer=None,
        )
        self.toxicity_scorer = ToxicityScorer(
            toxicity_model=None,
            toxicity_tokenizer=None,
            harmful_request_model=None,
            harmful_request_tokenizer=None,
        )

    def evaluate(self, rule_type: RuleType, span: Span) -> CEEvaluationResult:
        """
        Evaluate a guardrail rule on a span.

        Args:
            rule_type: The rule type (PII_DATA, PROMPT_INJECTION, or TOXICITY).
            span: The span to evaluate.

        Returns:
            CEEvaluationResult with annotation_score (1=pass, 0=fail) and
            annotation_description (JSON-serialized rule detail).

        Raises:
            ValueError: If rule_type is not one of the supported CE rule types.
        """
        match rule_type:
            case RuleType.PROMPT_INJECTION:
                return self._evaluate_prompt_injection(span)
            case RuleType.TOXICITY:
                return self._evaluate_toxicity(span)
            case RuleType.PII_DATA:
                return self._evaluate_pii(span)
            case _:
                raise ValueError(
                    f"Unsupported rule type for CE evaluation: {rule_type}. "
                    "Supported types: PII_DATA, PROMPT_INJECTION, TOXICITY."
                )

    def _evaluate_prompt_injection(self, span: Span) -> CEEvaluationResult:
        """Evaluate prompt injection on span input only."""
        text = span.input_content or ""
        if not text:
            logger.warning(
                "Span %s has no input content for PROMPT_INJECTION evaluation",
                span.span_id,
            )
        score_request = ScoreRequest(
            rule_type=RuleType.PROMPT_INJECTION,
            user_prompt=text,
        )
        rule_score = self.prompt_injection_classifier.score(score_request)
        return self._to_result(rule_score)

    def _evaluate_toxicity(self, span: Span) -> CEEvaluationResult:
        """Evaluate toxicity on span output only."""
        text = span.output_content or ""
        if not text:
            logger.warning(
                "Span %s has no output content for TOXICITY evaluation",
                span.span_id,
            )
        score_request = ScoreRequest(
            rule_type=RuleType.TOXICITY,
            scoring_text=text,
        )
        rule_score = self.toxicity_scorer.score(score_request)
        return self._to_result(rule_score)

    def _evaluate_pii(self, span: Span) -> CEEvaluationResult:
        """Evaluate PII on both span input and output."""
        input_score: Optional[RuleScore] = None
        output_score: Optional[RuleScore] = None

        if span.input_content:
            input_score = self.pii_classifier.score(
                ScoreRequest(
                    rule_type=RuleType.PII_DATA,
                    scoring_text=span.input_content,
                )
            )
        if span.output_content:
            output_score = self.pii_classifier.score(
                ScoreRequest(
                    rule_type=RuleType.PII_DATA,
                    scoring_text=span.output_content,
                )
            )

        return self._combine_pii_results(input_score, output_score)

    def _combine_pii_results(
        self,
        input_score: Optional[RuleScore],
        output_score: Optional[RuleScore],
    ) -> CEEvaluationResult:
        """Combine PII results from input and output into a single CEEvaluationResult."""
        input_failed = (
            input_score is not None and input_score.result == RuleResultEnum.FAIL
        )
        output_failed = (
            output_score is not None and output_score.result == RuleResultEnum.FAIL
        )

        if not input_failed and not output_failed:
            return CEEvaluationResult(
                annotation_score=1,
                annotation_description=json.dumps(
                    {"result": RuleResultEnum.PASS.value}
                ),
            )

        all_pii_results: list[str] = []
        all_pii_entities: list[dict] = []

        for score, target in [(input_score, "input"), (output_score, "output")]:
            if score is not None and score.result == RuleResultEnum.FAIL and score.details:
                if score.details.pii_results:
                    all_pii_results.extend(e.value for e in score.details.pii_results)
                if score.details.pii_entities:
                    for entity in score.details.pii_entities:
                        all_pii_entities.append(
                            {
                                "target": target,
                                "entity": entity.entity.value,
                                "span": entity.span,
                                "confidence": entity.confidence,
                            }
                        )

        unique_pii_results = sorted(set(all_pii_results))
        description = {
            "result": RuleResultEnum.FAIL.value,
            "message": f"PII found in data: {', '.join(unique_pii_results)}",
            "pii_results": unique_pii_results,
            "pii_entities": all_pii_entities,
        }
        return CEEvaluationResult(
            annotation_score=0,
            annotation_description=json.dumps(description),
        )

    def _to_result(self, rule_score: RuleScore) -> CEEvaluationResult:
        """Convert a RuleScore to a CEEvaluationResult."""
        annotation_score = 1 if rule_score.result == RuleResultEnum.PASS else 0
        description: dict = {"result": rule_score.result.value}

        if rule_score.details:
            if rule_score.details.message:
                description["message"] = rule_score.details.message
            if rule_score.details.toxicity_score:
                description["toxicity_score"] = (
                    rule_score.details.toxicity_score.model_dump()
                )
            if rule_score.details.pii_results:
                description["pii_results"] = [
                    e.value for e in rule_score.details.pii_results
                ]
            if rule_score.details.pii_entities:
                description["pii_entities"] = [
                    {
                        "entity": e.entity.value,
                        "span": e.span,
                        "confidence": e.confidence,
                    }
                    for e in rule_score.details.pii_entities
                ]

        return CEEvaluationResult(
            annotation_score=annotation_score,
            annotation_description=json.dumps(description),
        )
