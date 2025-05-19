import os
from unittest.mock import Mock, patch

import pytest
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from schemas.enums import MetricType, ToolSelectionScore, ToolUsageScore
from schemas.metric_schemas import MetricScore
from scorer.metrics.tool_selection.tool_selection import ToolSelectionCorrectnessScorer
from utils import utils

os.environ[utils.constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"
os.environ[utils.constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"


@patch("scorer.metrics.tool_selection.tool_selection.get_model")
@patch("scorer.metrics.tool_selection.tool_selection.OutputFixingParser")
@patch("scorer.metrics.tool_selection.tool_selection.PromptTemplate")
@patch("scorer.metrics.tool_selection.tool_selection.LLMChain")
@pytest.mark.unit_tests
def test_tool_selection_correctness_scorer_init(mock_llm_chain, mock_prompt_template, mock_fixing_parser, mock_get_model):
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
    
    assert isinstance(score, MetricScore)
    assert score.metric == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.value == ToolSelectionScore.CORRECT
    assert score.details.tool_usage.value == ToolUsageScore.CORRECT
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
    
    assert isinstance(score, MetricScore)
    assert score.metric == MetricType.TOOL_SELECTION
    assert score.details.tool_selection.value == ToolSelectionScore.UNAVAILABLE
    assert score.details.tool_usage.value == ToolUsageScore.UNAVAILABLE
    assert score.prompt_tokens == 0
    assert score.completion_tokens == 0 