from unittest.mock import patch

import pytest
from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.custom_exceptions import LLMContentFilterException, LLMExecutionException
from schemas.scorer_schemas import Example, RuleScore, ScoreRequest
from scorer.checks.sensitive_data.custom_examples import SensitiveDataCustomExamples
from services.guardrails.judge_executor import JudgeCallResult
from utils import constants

pytestmark = pytest.mark.unit_tests


@pytest.mark.parametrize("hint", [None, "specific individual's medical conditions"])
@pytest.mark.parametrize(
    ("output", "expected"), [("no", RuleResultEnum.PASS), ("yes", RuleResultEnum.FAIL)]
)
def test_sensitive_data_classification(output, expected, hint):
    request = ScoreRequest(
        rule_type=RuleType.MODEL_SENSITIVE_DATA,
        user_prompt="Test prompt",
        hint=hint,
        examples=[
            Example(
                exampleInput="test example",
                ruleOutput=RuleScore(result=RuleResultEnum.FAIL),
            )
        ],
    )
    tokens = LLMTokenConsumption(prompt_tokens=10, completion_tokens=5)
    with patch(
        "services.guardrails.judge_executor.JudgeEvaluation.complete",
        return_value=JudgeCallResult(output, None, tokens),
    ) as complete:
        score = SensitiveDataCustomExamples().score(request)
    assert score.result is expected
    assert score.details is None
    assert score.prompt_tokens == 10
    assert score.completion_tokens == 5
    prompt = complete.call_args.args[0][0].content
    assert "test example" in prompt
    if hint:
        assert hint in prompt


def test_score_no_examples():
    request = ScoreRequest(rule_type=RuleType.MODEL_SENSITIVE_DATA)
    with pytest.raises(ValueError):
        SensitiveDataCustomExamples().score(request)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            LLMExecutionException("untrusted provider detail"),
            constants.ERROR_DEFAULT_RULE_ENGINE,
        ),
        (
            LLMContentFilterException(),
            "GenAI Engine was unable to evaluate due to an upstream content policy",
        ),
    ],
)
def test_llm_execution_exception_handling(error, message):
    request = ScoreRequest(
        rule_type=RuleType.MODEL_SENSITIVE_DATA,
        examples=[
            Example(
                exampleInput="test example",
                ruleOutput=RuleScore(result=RuleResultEnum.FAIL),
            )
        ],
    )
    with patch(
        "services.guardrails.judge_executor.JudgeEvaluation.complete", side_effect=error
    ):
        score = SensitiveDataCustomExamples().score(request)
    assert score.result == RuleResultEnum.UNAVAILABLE
    assert score.details.message == message
