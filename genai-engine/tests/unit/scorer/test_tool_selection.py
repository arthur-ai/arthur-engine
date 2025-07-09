import os
from unittest.mock import Mock, patch

import pytest

from schemas.enums import MetricType, ToolClassEnum, ToolSelectionScore, ToolUsageScore
from schemas.metric_schemas import MetricRequest, MetricResult
from scorer.metrics.tool_selection.tool_selection import ToolSelectionCorrectnessScorer
from utils import utils

os.environ[utils.constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = (
    "1::2/::3"
)
os.environ[utils.constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"


@patch("scorer.metrics.tool_selection.tool_selection.get_model")
@patch("scorer.metrics.tool_selection.tool_selection.OutputFixingParser")
@patch("scorer.metrics.tool_selection.tool_selection.PromptTemplate")
@patch("scorer.metrics.tool_selection.tool_selection.LLMChain")
@pytest.mark.unit_tests
def test_tool_selection_correctness_scorer_init(
    mock_llm_chain, mock_prompt_template, mock_fixing_parser, mock_get_model
):
    # Arrange & Act
    scorer = ToolSelectionCorrectnessScorer()

    # Assert
    mock_get_model.assert_called_once()
    assert mock_fixing_parser.from_llm.call_count == 2
    assert mock_prompt_template.from_template.call_count == 2
    assert mock_llm_chain.call_count == 2
    assert scorer.tool_selection_chain is not None
    assert scorer.tool_usage_chain is not None


@patch.object(ToolSelectionCorrectnessScorer, "_invoke_chain_tool_selection")
@pytest.mark.unit_tests
def test_score_tool_selection(mock_invoke_chain):
    # Arrange
    mock_invoke_chain.return_value = {"value": 1, "justification": "Test justification"}

    scorer = ToolSelectionCorrectnessScorer()
    mock_request = Mock(
        system_prompt="Test system prompt",
        user_prompt="Test prompt",
        selected_tools=["tool1", "tool2"],
        available_tools=["tool1", "tool2", "tool3"],
        context="Test context",
    )

    # Act
    score = scorer.score_tool_selection(mock_request)

    # Assert
    mock_invoke_chain.assert_called_once()
    assert score == ToolSelectionScore.CORRECT


@patch.object(ToolSelectionCorrectnessScorer, "_invoke_chain_tool_usage")
@pytest.mark.unit_tests
def test_score_tool_usage(mock_invoke_chain):
    # Arrange
    mock_invoke_chain.return_value = {"value": 2, "justification": "Test justification"}

    scorer = ToolSelectionCorrectnessScorer()
    mock_request = Mock(
        system_prompt="Test system prompt",
        user_prompt="Test prompt",
        selected_tools=["tool1", "tool2"],
        tool_parameters={"tool1": {"param1": "value1"}, "tool2": {"param2": "value2"}},
        context="Test context",
    )

    # Act
    score = scorer.score_tool_usage(mock_request)

    # Assert
    mock_invoke_chain.assert_called_once()
    assert score == ToolUsageScore.UNAVAILABLE


@patch.object(ToolSelectionCorrectnessScorer, "score_tool_selection")
@patch.object(ToolSelectionCorrectnessScorer, "score_tool_usage")
@pytest.mark.unit_tests
def test_score(mock_score_tool_usage, mock_score_tool_selection):
    # Arrange
    mock_score_tool_selection.return_value = ToolSelectionScore.CORRECT
    mock_score_tool_usage.return_value = ToolUsageScore.CORRECT

    scorer = ToolSelectionCorrectnessScorer()
    mock_request = Mock(
        system_prompt="Test system prompt",
        user_prompt="Test prompt",
        selected_tools=["tool1"],
        tool_parameters={"tool1": {"param1": "value1"}},
        available_tools=["tool1", "tool2", "tool3"],
        context="Test context",
    )

    # Act
    score = scorer.score(mock_request)

    # Assert
    mock_score_tool_selection.assert_called_once_with(mock_request)
    mock_score_tool_usage.assert_called_once_with(mock_request)

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.CORRECT
    assert score.details.tool_selection.tool_usage == ToolClassEnum.CORRECT
    assert score.prompt_tokens == 0
    assert score.completion_tokens == 0


@patch.object(ToolSelectionCorrectnessScorer, "score_tool_selection")
@patch.object(ToolSelectionCorrectnessScorer, "score_tool_usage")
@pytest.mark.unit_tests
def test_score_with_exceptions(mock_score_tool_usage, mock_score_tool_selection):
    # Arrange
    mock_score_tool_selection.side_effect = Exception("Test exception")
    mock_score_tool_usage.side_effect = Exception("Test exception")

    scorer = ToolSelectionCorrectnessScorer()
    mock_request = Mock(
        system_prompt="Test system prompt",
        user_prompt="Test prompt",
        selected_tools=["tool1"],
        tool_parameters={"tool1": {"param1": "value1"}},
        available_tools=["tool1", "tool2", "tool3"],
        context="Test context",
    )

    # Act
    score = scorer.score(mock_request)

    # Assert
    mock_score_tool_selection.assert_called_once_with(mock_request)
    mock_score_tool_usage.assert_called_once_with(mock_request)

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.NOT_AVAILABLE
    assert score.details.tool_selection.tool_usage == ToolClassEnum.NOT_AVAILABLE
    assert score.prompt_tokens == 0
    assert score.completion_tokens == 0


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


@pytest.mark.asyncio
async def test_score_with_successful_tool_selection_and_usage(
    scorer,
    mock_tool_selection_chain,
    mock_tool_usage_chain,
    mocker,
):
    # Mock chain responses
    mock_tool_selection_chain.invoke.return_value = {
        "tool_selection": 1,
        "tool_selection_reason": "Correct tool was selected",
    }
    mock_tool_usage_chain.invoke.return_value = {
        "tool_usage": 1,
        "tool_usage_reason": "Tool was used correctly",
    }

    # Mock the token consumption
    mocker.patch(
        "scorer.metrics.tool_selection.tool_selection.get_llm_executor"
    ).return_value.execute.side_effect = [
        (
            {
                "tool_selection": 1,
                "tool_selection_reason": "Correct tool was selected",
            },
            type("MockTokens", (), {"prompt_tokens": 100, "completion_tokens": 50}),
        ),
        (
            {
                "tool_usage": 1,
                "tool_usage_reason": "Tool was used correctly",
            },
            type("MockTokens", (), {"prompt_tokens": 100, "completion_tokens": 50}),
        ),
    ]

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

    config = {}
    score = scorer.score(request, config)

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.CORRECT
    assert score.details.tool_selection.tool_usage == ToolClassEnum.CORRECT
    assert score.prompt_tokens == 200
    assert score.completion_tokens == 100


@pytest.mark.asyncio
async def test_score_with_no_tool_selection(
    scorer,
    mock_tool_selection_chain,
    mock_tool_usage_chain,
    mocker,
):
    # Mock chain responses
    mock_tool_selection_chain.invoke.return_value = {
        "tool_selection": 2,
        "tool_selection_reason": "No tool was needed",
    }

    # Mock the token consumption
    mocker.patch(
        "scorer.metrics.tool_selection.tool_selection.get_llm_executor"
    ).return_value.execute.side_effect = [
        (
            {
                "tool_selection": 2,
                "tool_selection_reason": "No tool was needed",
            },
            type("MockTokens", (), {"prompt_tokens": 100, "completion_tokens": 50}),
        ),
    ]

    request = MetricRequest(
        system_prompt="Test system prompt",
        user_query="Hello, how are you?",
        context=[
            {"role": "user", "value": "Hello, how are you?"},
            {"role": "assistant", "value": "I'm doing well, thank you!"},
        ],
    )

    config = {}
    score = scorer.score(request, config)

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.tool_selection == ToolClassEnum.NOT_AVAILABLE
    assert score.details.tool_selection.tool_usage == ToolClassEnum.NOT_AVAILABLE
    assert score.prompt_tokens == 100
    assert score.completion_tokens == 50
