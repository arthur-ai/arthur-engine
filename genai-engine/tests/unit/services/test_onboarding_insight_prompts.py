"""The onboarding insight prompts keep what the model writes for customers short and safe.

A verdict's reason is shown to the agent's owner, so it names a general theme in one
sentence and never carries trace ids or anything sensitive from the traces.
"""

import pytest
from arthur_common.models.llm_model_providers import LLMResponseFormat

from repositories.system_task_repository import onboarding_insight_prompt
from services.onboarding.insight_prompts import (
    ONBOARDING_INSIGHT_QUESTIONS,
    ONBOARDING_INSIGHT_SYSTEM_PROMPT,
)

SENSITIVE_CLASSES = [
    "API keys",
    "secrets",
    "tokens",
    "passwords",
    "URLs",
    "hostnames",
    "IP addresses",
    "environment variable names",
    "email addresses",
    "personal data",
    "trace ids",
    "quotes from the traces",
]


def _schema(kind: str):
    config = onboarding_insight_prompt(kind).config
    assert config is not None
    assert isinstance(config.response_format, LLMResponseFormat)
    assert config.response_format.json_schema is not None
    return config.response_format.json_schema


@pytest.mark.unit_tests
def test_system_prompt_lists_what_never_to_output() -> None:
    assert "Never output" in ONBOARDING_INSIGHT_SYSTEM_PROMPT
    for sensitive in SENSITIVE_CLASSES:
        assert sensitive in ONBOARDING_INSIGHT_SYSTEM_PROMPT, sensitive


@pytest.mark.unit_tests
def test_system_prompt_keeps_trace_ids_to_matched_traces() -> None:
    assert (
        "matched_traces is the only place trace ids belong; it is used internally "
        "for counts and never shown." in ONBOARDING_INSIGHT_SYSTEM_PROMPT
    )
    assert "one sentence naming the general theme" in ONBOARDING_INSIGHT_SYSTEM_PROMPT


@pytest.mark.unit_tests
def test_reason_is_one_sentence_with_no_trace_details() -> None:
    for kind in ONBOARDING_INSIGHT_QUESTIONS:
        description = _schema(kind).schema.properties["reason"].description

        assert description == (
            "One sentence naming the general theme. No trace ids, span names, quotes, "
            "URLs, hostnames, keys, tokens, environment variable names, emails or "
            "personal data."
        )
        assert "citing" not in description


@pytest.mark.unit_tests
def test_verdict_schema_keeps_its_shape() -> None:
    fields = ["kind", "fired", "matched_traces", "example_span_name", "reason"]
    for kind in ONBOARDING_INSIGHT_QUESTIONS:
        schema = _schema(kind)

        assert schema.name == "onboarding_insight_verdict"
        assert schema.strict
        assert list(schema.schema.properties) == fields
        assert schema.schema.required == fields
        assert schema.schema.additionalProperties is False
        assert schema.schema.properties["fired"].enum == ["yes", "no", "cannot_tell"]
        assert schema.schema.properties["matched_traces"].type == "array"
