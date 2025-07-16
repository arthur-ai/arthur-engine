import os
from unittest.mock import Mock, patch

import pytest

from schemas.enums import MetricType, ToolClassEnum
from schemas.metric_schemas import MetricRequest
from schemas.internal_schemas import MetricResult
from scorer.metrics.tool_selection.tool_selection import ToolSelectionCorrectnessScorer
from utils import utils

os.environ[utils.constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = (
    "1::2/::3"
)
os.environ[utils.constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"


@patch("scorer.metrics.tool_selection.tool_selection.get_model")
@patch("scorer.metrics.tool_selection.tool_selection.get_tool_selection_chain")
@patch("scorer.metrics.tool_selection.tool_selection.get_tool_usage_chain")
@pytest.mark.unit_tests
def test_tool_selection_correctness_scorer_init(
    mock_get_tool_usage_chain,
    mock_get_tool_selection_chain,
    mock_get_model,
):
    # Arrange & Act
    scorer = ToolSelectionCorrectnessScorer()

    # Assert
    assert scorer.tool_selection_chain is not None
    assert scorer.tool_usage_chain is not None


@patch.object(ToolSelectionCorrectnessScorer, "invoke_chain")
@pytest.mark.unit_tests
def test_score_tool_selection_and_usage(mock_invoke_chain):
    # Arrange
    mock_invoke_chain.return_value = (
        {
            "tool_selection": 1,
            "tool_selection_reason": "Correct tool was selected",
            "tool_usage": 1,
            "tool_usage_reason": "Tool was used correctly",
        },
        {"prompt_tokens": 100, "completion_tokens": 50}
    )

    scorer = ToolSelectionCorrectnessScorer()
    mock_request = Mock(
        system_prompt="Test system prompt",
        user_query="Test prompt",
        context="Test context",
    )

    # Act
    score = scorer.score(mock_request, {})

    # Assert
    mock_invoke_chain.assert_called_once()
    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.CORRECT_TOOL_SELECTED
    assert score.details.tool_selection.tool_usage == ToolClassEnum.CORRECT_TOOL_SELECTED


@patch.object(ToolSelectionCorrectnessScorer, "invoke_chain")
@pytest.mark.unit_tests
def test_score_with_no_tool_selected(mock_invoke_chain):
    # Arrange
    mock_invoke_chain.return_value = (
        {
            "tool_selection": 2,
            "tool_selection_reason": "No tool was needed",
            "tool_usage": 2,
            "tool_usage_reason": "No tool usage required",
        },
        {"prompt_tokens": 100, "completion_tokens": 50}
    )

    scorer = ToolSelectionCorrectnessScorer()
    mock_request = Mock(
        system_prompt="Test system prompt",
        user_query="Test prompt",
        context="Test context",
    )

    # Act
    score = scorer.score(mock_request, {})

    # Assert
    mock_invoke_chain.assert_called_once()
    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.NO_TOOL_SELECTED
    assert score.details.tool_selection.tool_usage == ToolClassEnum.NO_TOOL_SELECTED


@patch.object(ToolSelectionCorrectnessScorer, "invoke_chain")
@pytest.mark.unit_tests
def test_score_with_wrong_tool_selected(mock_invoke_chain):
    # Arrange
    mock_invoke_chain.return_value = (
        {
            "tool_selection": 0,
            "tool_selection_reason": "Wrong tool was selected",
            "tool_usage": 0,
            "tool_usage_reason": "Tool was used incorrectly",
        },
        {"prompt_tokens": 100, "completion_tokens": 50}
    )

    scorer = ToolSelectionCorrectnessScorer()
    mock_request = Mock(
        system_prompt="Test system prompt",
        user_query="Test prompt",
        context="Test context",
    )

    # Act
    score = scorer.score(mock_request, {})

    # Assert
    mock_invoke_chain.assert_called_once()
    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.WRONG_TOOL_SELECTED
    assert score.details.tool_selection.tool_usage == ToolClassEnum.WRONG_TOOL_SELECTED


@pytest.fixture
def mock_tool_selection_chain(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_tool_usage_chain(mocker):
    return mocker.MagicMock()


@pytest.fixture
def scorer(mock_tool_selection_chain, mock_tool_usage_chain):
    scorer = ToolSelectionCorrectnessScorer()
    scorer.tool_selection_chain = mock_tool_selection_chain
    scorer.tool_usage_chain = mock_tool_usage_chain
    return scorer


def test_tool_selection_scorer_initialization():
    scorer = ToolSelectionCorrectnessScorer()
    assert scorer.tool_selection_chain is not None
    assert scorer.tool_usage_chain is not None


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_score_with_successful_tool_selection_and_usage_fixed(mock_get_llm_executor):
    # Arrange
    mock_execute = Mock()
    mock_execute.side_effect = [
        (
            {
                "tool_selection": 1,
                "tool_selection_reason": "Correct tool was selected",
            },
            type("MockTokens", (), {"prompt_tokens": 100, "completion_tokens": 50})(),
        ),
        (
            {
                "tool_usage": 1,
                "tool_usage_reason": "Tool was used correctly",
            },
            type("MockTokens", (), {"prompt_tokens": 100, "completion_tokens": 50})(),
        ),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="Test system prompt",
        user_query="What's the weather like?",
        context=[
            {"role": "user", "value": "What's the weather like?"},
            {"role": "assistant", "value": "WeatherTool", "args": {"city": "NYC"}},
            {
                "role": "tool",
                "value": '[{"name": "WeatherTool", "result": {"temperature": "20°C"}}]',
            },
            {"role": "assistant", "value": "The temperature in NYC is 20°C."},
        ],
    )

    # Act
    score = scorer.score(request, {})

    # Assert
    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.CORRECT_TOOL_SELECTED
    assert score.details.tool_selection.tool_usage == ToolClassEnum.CORRECT_TOOL_SELECTED
    assert score.prompt_tokens == 200
    assert score.completion_tokens == 100


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_score_with_no_tool_selection_fixed(mock_get_llm_executor):
    # Arrange
    mock_execute = Mock()
    mock_execute.side_effect = [
        (
            {
                "tool_selection": 2,
                "tool_selection_reason": "No tool was needed",
            },
            type("MockTokens", (), {"prompt_tokens": 100, "completion_tokens": 50})(),
        ),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="Test system prompt",
        user_query="Hello, how are you?",
        context=[
            {"role": "user", "value": "Hello, how are you?"},
            {"role": "assistant", "value": "I'm doing well, thank you!"},
        ],
    )

    # Act
    score = scorer.score(request, {})

    # Assert
    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.NO_TOOL_SELECTED
    assert score.details.tool_selection.tool_usage == ToolClassEnum.NO_TOOL_SELECTED
    assert score.prompt_tokens == 100
    assert score.completion_tokens == 50
