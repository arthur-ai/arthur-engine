import os
from unittest.mock import Mock, patch

import pytest
from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import MetricType, ToolClassEnum
from arthur_common.models.metric_schemas import MetricRequest

from schemas.internal_schemas import MetricResult
from scorer.metrics.tool_selection.tool_selection import ToolSelectionCorrectnessScorer
from utils import utils

os.environ[utils.constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = (
    "1::2/::3"
)
os.environ[utils.constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_correctness_scorer_init(mock_get_llm_executor):
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = True

    # Act
    scorer = ToolSelectionCorrectnessScorer()

    # Assert - verify the scorer can be initialized and has the expected methods
    assert hasattr(scorer, "_get_chains")
    assert hasattr(scorer, "score")
    assert hasattr(scorer, "invoke_chain")

    # Verify _get_chains returns a tuple of 2 elements (selection_chain, usage_chain)
    chains = scorer._get_chains()
    assert isinstance(chains, tuple)
    assert len(chains) == 2


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
        {"prompt_tokens": 100, "completion_tokens": 50},
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
    assert score.details.tool_selection.tool_selection == ToolClassEnum.CORRECT
    assert score.details.tool_selection.tool_usage == ToolClassEnum.CORRECT


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
        {"prompt_tokens": 100, "completion_tokens": 50},
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
    assert score.details.tool_selection.tool_selection == ToolClassEnum.NA
    assert score.details.tool_selection.tool_usage == ToolClassEnum.NA


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
        {"prompt_tokens": 100, "completion_tokens": 50},
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
    assert score.details.tool_selection.tool_selection == ToolClassEnum.INCORRECT
    assert score.details.tool_selection.tool_usage == ToolClassEnum.INCORRECT


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
    assert score.details.tool_selection.tool_selection == ToolClassEnum.CORRECT
    assert score.details.tool_selection.tool_usage == ToolClassEnum.CORRECT
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
    assert score.details.tool_selection.tool_selection == ToolClassEnum.NA
    assert score.details.tool_selection.tool_usage == ToolClassEnum.NA
    assert score.prompt_tokens == 100
    assert score.completion_tokens == 50


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_structured_outputs(mock_get_llm_executor):
    """Test ToolSelectionCorrectnessScorer with structured outputs enabled"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = True
    mock_execute = Mock()
    mock_execute.side_effect = [
        (
            {
                "tool_selection": 1,
                "tool_selection_reason": "Correct tool was selected using structured output",
            },
            LLMTokenConsumption(prompt_tokens=120, completion_tokens=60),
        ),
        (
            {
                "tool_usage": 1,
                "tool_usage_reason": "Tool was used correctly with structured output",
            },
            LLMTokenConsumption(prompt_tokens=110, completion_tokens=55),
        ),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="You are a helpful assistant with access to weather tools.",
        user_query="What's the temperature in Paris?",
        context=[
            {"role": "user", "value": "What's the temperature in Paris?"},
            {"role": "assistant", "value": "WeatherTool", "args": {"city": "Paris"}},
            {
                "role": "tool",
                "value": '[{"name": "WeatherTool", "result": {"temperature": "15°C"}}]',
            },
            {"role": "assistant", "value": "The temperature in Paris is 15°C."},
        ],
    )

    # Act
    result = scorer.score(request, {})

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.TOOL_SELECTION
    assert result.details.tool_selection.tool_selection == ToolClassEnum.CORRECT
    assert result.details.tool_selection.tool_usage == ToolClassEnum.CORRECT
    assert (
        result.details.tool_selection.tool_selection_reason
        == "Correct tool was selected using structured output"
    )
    assert (
        result.details.tool_selection.tool_usage_reason
        == "Tool was used correctly with structured output"
    )
    assert result.prompt_tokens == 230
    assert result.completion_tokens == 115


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_legacy_outputs(mock_get_llm_executor):
    """Test ToolSelectionCorrectnessScorer with legacy/unstructured outputs"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = False
    mock_execute = Mock()
    mock_execute.side_effect = [
        (
            {
                "tool_selection": 0,
                "tool_selection_reason": "Wrong tool was selected, detected via legacy output",
            },
            LLMTokenConsumption(prompt_tokens=140, completion_tokens=70),
        ),
        (
            {
                "tool_usage": 0,
                "tool_usage_reason": "Tool was used incorrectly, detected via legacy output",
            },
            LLMTokenConsumption(prompt_tokens=130, completion_tokens=65),
        ),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="You are a helpful assistant with access to weather and calendar tools.",
        user_query="What's the weather like today?",
        context=[
            {"role": "user", "value": "What's the weather like today?"},
            {"role": "assistant", "value": "CalendarTool", "args": {"date": "today"}},
            {
                "role": "tool",
                "value": '[{"name": "CalendarTool", "result": {"events": []}}]',
            },
            {"role": "assistant", "value": "You have no events today."},
        ],
    )

    # Act
    result = scorer.score(request, {})

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.TOOL_SELECTION
    assert result.details.tool_selection.tool_selection == ToolClassEnum.INCORRECT
    assert result.details.tool_selection.tool_usage == ToolClassEnum.INCORRECT
    assert (
        result.details.tool_selection.tool_selection_reason
        == "Wrong tool was selected, detected via legacy output"
    )
    assert (
        result.details.tool_selection.tool_usage_reason
        == "Tool was used incorrectly, detected via legacy output"
    )
    assert result.prompt_tokens == 270
    assert result.completion_tokens == 135


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_no_tool_structured(mock_get_llm_executor):
    """Test ToolSelectionCorrectnessScorer when no tool is needed (structured outputs)"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = True
    mock_execute = Mock()
    mock_execute.side_effect = [
        (
            {
                "tool_selection": 2,
                "tool_selection_reason": "No tool was needed for this query (structured)",
            },
            LLMTokenConsumption(prompt_tokens=100, completion_tokens=50),
        ),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="You are a helpful assistant.",
        user_query="Hello, how are you?",
        context=[
            {"role": "user", "value": "Hello, how are you?"},
            {
                "role": "assistant",
                "value": "Hello! I'm doing well, thank you for asking.",
            },
        ],
    )

    # Act
    result = scorer.score(request, {})

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.TOOL_SELECTION
    assert result.details.tool_selection.tool_selection == ToolClassEnum.NA
    assert result.details.tool_selection.tool_usage == ToolClassEnum.NA
    assert (
        result.details.tool_selection.tool_selection_reason
        == "No tool was needed for this query (structured)"
    )
    assert (
        result.details.tool_selection.tool_usage_reason
        == "Could not evaluate tool usage"
    )
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_no_tool_legacy(mock_get_llm_executor):
    """Test ToolSelectionCorrectnessScorer when no tool is needed (legacy outputs)"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = False
    mock_execute = Mock()
    mock_execute.side_effect = [
        (
            {
                "tool_selection": 2,
                "tool_selection_reason": "No tool was needed for this query (legacy)",
            },
            LLMTokenConsumption(prompt_tokens=110, completion_tokens=55),
        ),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="You are a helpful assistant.",
        user_query="What's 2 + 2?",
        context=[
            {"role": "user", "value": "What's 2 + 2?"},
            {"role": "assistant", "value": "2 + 2 equals 4."},
        ],
    )

    # Act
    result = scorer.score(request, {})

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.TOOL_SELECTION
    assert result.details.tool_selection.tool_selection == ToolClassEnum.NA
    assert result.details.tool_selection.tool_usage == ToolClassEnum.NA
    assert (
        result.details.tool_selection.tool_selection_reason
        == "No tool was needed for this query (legacy)"
    )
    assert (
        result.details.tool_selection.tool_usage_reason
        == "Could not evaluate tool usage"
    )
    assert result.prompt_tokens == 110
    assert result.completion_tokens == 55


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_chain_selection_structured(mock_get_llm_executor):
    """Test that the scorer correctly selects structured output chains"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = True

    scorer = ToolSelectionCorrectnessScorer()

    # Mock the chains to verify which ones are called
    with (
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_selection_chain_structured",
        ) as mock_structured_selection,
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_usage_chain_structured",
        ) as mock_structured_usage,
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_selection_chain_legacy",
        ) as mock_legacy_selection,
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_usage_chain_legacy",
        ) as mock_legacy_usage,
    ):

        # Act
        chains = scorer._get_chains()

        # Assert
        mock_structured_selection.assert_called_once()
        mock_structured_usage.assert_called_once()
        mock_legacy_selection.assert_not_called()
        mock_legacy_usage.assert_not_called()


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_chain_selection_legacy(mock_get_llm_executor):
    """Test that the scorer correctly selects legacy output chains"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = False

    scorer = ToolSelectionCorrectnessScorer()

    # Mock the chains to verify which ones are called
    with (
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_selection_chain_structured",
        ) as mock_structured_selection,
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_usage_chain_structured",
        ) as mock_structured_usage,
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_selection_chain_legacy",
        ) as mock_legacy_selection,
        patch(
            "scorer.metrics.tool_selection.tool_selection.get_tool_usage_chain_legacy",
        ) as mock_legacy_usage,
    ):

        # Act
        chains = scorer._get_chains()

        # Assert
        mock_structured_selection.assert_not_called()
        mock_structured_usage.assert_not_called()
        mock_legacy_selection.assert_called_once()
        mock_legacy_usage.assert_called_once()


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_exception_handling_structured(mock_get_llm_executor):
    """Test exception handling in structured output mode"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = True
    mock_execute = Mock()
    # First call succeeds, second call fails
    mock_execute.side_effect = [
        (
            {
                "tool_selection": 1,
                "tool_selection_reason": "Tool selection worked",
            },
            LLMTokenConsumption(prompt_tokens=100, completion_tokens=50),
        ),
        Exception("Tool usage evaluation failed"),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="You are a helpful assistant with tools.",
        user_query="What's the weather?",
        context=[
            {"role": "user", "value": "What's the weather?"},
            {"role": "assistant", "value": "WeatherTool", "args": {"city": "NYC"}},
        ],
    )

    # Act
    result = scorer.score(request, {})

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.TOOL_SELECTION
    assert result.details.tool_selection.tool_selection == ToolClassEnum.CORRECT
    assert (
        result.details.tool_selection.tool_usage == ToolClassEnum.NA
    )  # Default fallback
    assert (
        result.details.tool_selection.tool_selection_reason == "Tool selection worked"
    )
    assert (
        result.details.tool_selection.tool_usage_reason
        == "Could not evaluate tool usage"
    )
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50


@patch("scorer.metrics.tool_selection.tool_selection.get_llm_executor")
@pytest.mark.unit_tests
def test_tool_selection_scorer_exception_handling_legacy(mock_get_llm_executor):
    """Test exception handling in legacy output mode"""
    # Arrange
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = False
    mock_execute = Mock()
    # Both calls fail
    mock_execute.side_effect = [
        Exception("Tool selection evaluation failed"),
        Exception("Tool usage evaluation failed"),
    ]
    mock_get_llm_executor.return_value.execute = mock_execute

    scorer = ToolSelectionCorrectnessScorer()
    request = MetricRequest(
        system_prompt="You are a helpful assistant with tools.",
        user_query="What's the weather?",
        context=[
            {"role": "user", "value": "What's the weather?"},
            {"role": "assistant", "value": "WeatherTool", "args": {"city": "NYC"}},
        ],
    )

    # Act
    result = scorer.score(request, {})

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.TOOL_SELECTION
    assert (
        result.details.tool_selection.tool_selection == ToolClassEnum.NA
    )  # Default fallback
    assert (
        result.details.tool_selection.tool_usage == ToolClassEnum.NA
    )  # Default fallback
    assert (
        result.details.tool_selection.tool_selection_reason
        == "Could not evaluate tool selection"
    )
    assert (
        result.details.tool_selection.tool_usage_reason
        == "Could not evaluate tool usage"
    )
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0
