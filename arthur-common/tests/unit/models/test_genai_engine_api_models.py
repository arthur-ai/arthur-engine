import uuid
from datetime import datetime, timezone

import pytest
from arthur_common.models.genai_engine import (
    ExampleConfig,
    ExamplesConfig,
    KeywordsConfig,
    NewRuleRequest,
    PIIConfig,
    RegexConfig,
    RuleResponse,
    RuleScope,
    RuleType,
    ToxicityConfig,
)


@pytest.mark.parametrize(
    "genai_engine_rule",
    [
        (
            NewRuleRequest(
                name="keyword rule",
                type=RuleType.KEYWORD,
                apply_to_prompt=True,
                apply_to_response=True,
                config=KeywordsConfig(
                    keywords=["word1", "word2"],
                ),
            )
        ),
        (
            NewRuleRequest(
                name="regex rule",
                type=RuleType.REGEX,
                apply_to_prompt=True,
                apply_to_response=True,
                config=RegexConfig(
                    regex_patterns=[".*test.*"],
                ),
            )
        ),
        (
            NewRuleRequest(
                name="PII rule",
                type=RuleType.PII_DATA,
                apply_to_prompt=True,
                apply_to_response=True,
                config=PIIConfig(
                    disabled_pii_entities=[],
                    confidence_threshold=0.5,
                    allow_list=[],
                ),
            )
        ),
        (
            NewRuleRequest(
                name="PII rule all optional",
                type=RuleType.PII_DATA,
                apply_to_prompt=True,
                apply_to_response=True,
                config=PIIConfig(),
            )
        ),
        (
            NewRuleRequest(
                name="Toxicity rule",
                type=RuleType.TOXICITY,
                apply_to_prompt=True,
                apply_to_response=True,
                config=ToxicityConfig(
                    threshold=0.5,
                ),
            )
        ),
        (
            NewRuleRequest(
                name="Toxicity all defaults",
                type=RuleType.TOXICITY,
                apply_to_prompt=True,
                apply_to_response=True,
                config=ToxicityConfig(),
            )
        ),
        (
            NewRuleRequest(
                name="Hallucination rule",
                type=RuleType.MODEL_HALLUCINATION_V2,
                apply_to_prompt=False,
                apply_to_response=True,
                config=None,
            )
        ),
        (
            NewRuleRequest(
                name="Sensitive data rule",
                type=RuleType.MODEL_SENSITIVE_DATA,
                apply_to_prompt=True,
                apply_to_response=False,
                config=ExamplesConfig(
                    examples=[
                        ExampleConfig(
                            example="test",
                            result=True,
                        ),
                    ],
                    hint="test hint",
                ),
            )
        ),
        (
            NewRuleRequest(
                name="Prompt Injection rule",
                type=RuleType.PROMPT_INJECTION,
                apply_to_prompt=True,
                apply_to_response=False,
                config=None,
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="keyword rule",
                type=RuleType.KEYWORD,
                apply_to_prompt=True,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=KeywordsConfig(
                    keywords=["word1", "word2"],
                ),
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="regex rule",
                type=RuleType.REGEX,
                apply_to_prompt=True,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=RegexConfig(
                    regex_patterns=[".*test.*"],
                ),
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="PII rule",
                type=RuleType.PII_DATA,
                apply_to_prompt=True,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=PIIConfig(
                    disabled_pii_entities=[],
                    confidence_threshold=0.5,
                    allow_list=[],
                ),
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="PII rule all optional",
                type=RuleType.PII_DATA,
                apply_to_prompt=True,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=PIIConfig(),
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="Toxicity rule",
                type=RuleType.TOXICITY,
                apply_to_prompt=True,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=ToxicityConfig(
                    threshold=0.5,
                ),
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="Toxicity all defaults",
                type=RuleType.TOXICITY,
                apply_to_prompt=True,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=ToxicityConfig(),
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="Hallucination rule",
                type=RuleType.MODEL_HALLUCINATION_V2,
                apply_to_prompt=False,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=None,
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="Sensitive data rule",
                type=RuleType.MODEL_SENSITIVE_DATA,
                apply_to_prompt=True,
                apply_to_response=True,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=ExamplesConfig(
                    examples=[
                        ExampleConfig(
                            example="test",
                            result=True,
                        ),
                    ],
                    hint="test hint",
                ),
            )
        ),
        (
            RuleResponse(
                id=str(uuid.uuid4()),
                name="Prompt injection rule",
                type=RuleType.PROMPT_INJECTION,
                apply_to_prompt=True,
                apply_to_response=False,
                enabled=True,
                scope=RuleScope.TASK,
                created_at=int(round(datetime.now(timezone.utc).timestamp())),
                updated_at=int(round(datetime.now(timezone.utc).timestamp())),
                config=None,
            )
        ),
    ],
)
def test_genai_engine_api_models(
    genai_engine_rule: NewRuleRequest | RuleResponse,
) -> None:
    # validate a rule is the same after serialization
    genai_engine_rule_json = genai_engine_rule.model_dump_json()
    assert (
        type(genai_engine_rule).model_validate_json(genai_engine_rule_json)
        == genai_engine_rule
    )
