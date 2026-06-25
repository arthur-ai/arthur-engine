from arthur_common.models.enums import RuleResultEnum
from arthur_common.models.response_schemas import ExternalRuleResult
from pydantic import BaseModel, Field


class GuardrailSpanResult(BaseModel):
    """Payload serialized into a GUARDRAIL span's ``output.value`` attribute.

    The JSON shape is a contract with the frontend guardrail parser (read as
    ``span.raw_data.attributes.output.value`` after ingestion unflattens and
    JSON-parses it) — keep it stable. ``rule_results`` reuses ``ExternalRuleResult``
    so the span payload matches the validate HTTP response.
    """

    blocked: bool = Field(
        description="True when any rule result is Fail (the guardrail would block).",
    )
    blocked_reason: str | None = Field(
        default=None,
        description="Human-readable reason synthesized from the failed rules' messages.",
    )
    inference_id: str = Field(
        description="ID of the persisted inference this guardrail result belongs to.",
    )
    rule_results: list[ExternalRuleResult] = Field(
        description="Per-rule results, identical to the validate response payload.",
    )

    @classmethod
    def from_validation(
        cls,
        inference_id: str,
        rule_results: list[ExternalRuleResult],
    ) -> "GuardrailSpanResult":
        """Synthesize the payload: only ``Fail`` blocks (Skipped/Unavailable do not);
        the reason joins the failed rules' messages, falling back to rule names."""
        failed = [r for r in rule_results if r.result == RuleResultEnum.FAIL]
        blocked_reason = (
            "; ".join(
                (
                    r.details.message
                    if r.details is not None and r.details.message
                    else f"{r.name} failed"
                )
                for r in failed
            )
            or None
        )
        return cls(
            blocked=bool(failed),
            blocked_reason=blocked_reason,
            inference_id=inference_id,
            rule_results=rule_results,
        )
