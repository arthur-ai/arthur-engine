import os
from unittest import mock
from unittest.mock import patch

import pytest
import utils.constants
from langchain.schema import AIMessage
from langchain_openai import AzureChatOpenAI
from schemas.common_schemas import LLMTokenConsumption
from schemas.custom_exceptions import LLMContentFilterException, LLMExecutionException
from schemas.enums import RuleResultEnum, RuleType
from schemas.scorer_schemas import Example, RuleScore, ScoreRequest
from scorer.checks.sensitive_data.custom_examples import SensitiveDataCustomExamples

os.environ[utils.constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"
os.environ[utils.constants.GENAI_ENGINE_OPENAI_PROVIDER_ENV_VAR] = "Azure"

DEFAULT_TOKEN_CONSUMPTION = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)

BASE_CASE_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_SENSITIVE_DATA,
    context="Test Context",
    response="Test Response",
    examples=[
        Example(
            exampleInput="test example",
            ruleOutput=RuleScore(result=RuleResultEnum.FAIL),
        ),
    ],
)

HINT_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_SENSITIVE_DATA,
    context="Test Context",
    response="Test Response",
    examples=[
        Example(
            exampleInput="test example",
            ruleOutput=RuleScore(result=RuleResultEnum.FAIL),
        ),
    ],
    hint="specific individual's medical conditions",
)

NO_EXAMPLES_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_SENSITIVE_DATA,
    context="Test Context",
    response="Test Response",
)


@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@patch.object(AzureChatOpenAI, "__call__", lambda *args: AIMessage(content="no"))
@pytest.mark.unit_tests
def test_score_no_sensitive_data():
    # Create the scorer object
    scorer = SensitiveDataCustomExamples()
    score = scorer.score(BASE_CASE_REQUEST)

    # Assertions
    assert score.result is RuleResultEnum.PASS
    assert score.details is None


@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@patch.object(AzureChatOpenAI, "__call__", lambda *args: AIMessage(content="yes"))
@pytest.mark.unit_tests
def test_score_sensitive_data():
    # Create the scorer object
    scorer = SensitiveDataCustomExamples()
    score = scorer.score(BASE_CASE_REQUEST)

    # Assertions
    assert score.result is RuleResultEnum.FAIL
    assert score.details is None


@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@patch.object(AzureChatOpenAI, "__call__", lambda *args: AIMessage(content="no"))
@pytest.mark.unit_tests
def test_score_no_sensitive_data_with_hint():
    # Create the scorer object
    scorer = SensitiveDataCustomExamples()
    score = scorer.score(HINT_REQUEST)

    # Assertions
    assert score.result is RuleResultEnum.PASS
    assert score.details is None


@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@patch.object(AzureChatOpenAI, "__call__", lambda *args: AIMessage(content="yes"))
@pytest.mark.unit_tests
def test_score_sensitive_data_with_hint():
    # Create the scorer object
    scorer = SensitiveDataCustomExamples()
    score = scorer.score(HINT_REQUEST)

    # Assertions
    assert score.result is RuleResultEnum.FAIL
    assert score.details is None


@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_score_no_examples():
    # Set up the mock grader llm
    scorer = SensitiveDataCustomExamples()

    # Check that ValueError is raised if no examples are provided
    with pytest.raises(ValueError):
        scorer.score(NO_EXAMPLES_REQUEST)


class LLMContentExecutionException:
    pass


@pytest.mark.unit_tests
def test_llm_execution_exception_handling():
    with mock.patch.object(
        SensitiveDataCustomExamples,
        "prompt_llm",
        side_effect=LLMExecutionException("test error"),
    ):
        sensitive_data_rule = SensitiveDataCustomExamples()
        rule_score = sensitive_data_rule.score(BASE_CASE_REQUEST)

        assert rule_score.result == RuleResultEnum.UNAVAILABLE
        assert rule_score.details.message == "test error"

    with mock.patch.object(
        SensitiveDataCustomExamples,
        "prompt_llm",
        side_effect=LLMContentFilterException(),
    ):
        sensitive_data_rule = SensitiveDataCustomExamples()
        rule_score = sensitive_data_rule.score(BASE_CASE_REQUEST)

        assert rule_score.result == RuleResultEnum.UNAVAILABLE
        assert (
            rule_score.details.message
            == "GenAI Engine was unable to evaluate due to an upstream content policy"
        )
