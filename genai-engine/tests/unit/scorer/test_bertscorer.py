import os
from unittest.mock import MagicMock, Mock, patch

import pytest
import torch
from langchain.chat_models import AzureChatOpenAI

from schemas.enums import MetricType
from schemas.metric_schemas import MetricRequest, MetricResult
from scorer.metrics.relevance.relevance import QueryBertScorer, ResponseBertScorer
from utils import utils

os.environ[utils.constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = (
    "1::2/::3"
)
os.environ[utils.constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"

# DEFAULT_TOKEN_CONSUMPTION = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)


@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
def test_relevance_bertscorer_init(
    mock_bert_model,
):
    scorer = QueryBertScorer()
    assert scorer.model is mock_bert_model.return_value
    scorer = ResponseBertScorer()
    assert scorer.model is mock_bert_model.return_value


@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_user_query_bertscore(mock_bert_model):
    # Arrange
    expected_f_score = 0.6568
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_f_score]),
    )

    scorer = QueryBertScorer()
    mock_request = Mock(user_prompt="Test prompt", system_prompt="Test system prompt")

    # Act
    score = scorer.score(mock_request)

    # Assert
    mock_bert_model.return_value.score.assert_called_once_with(
        [mock_request.user_prompt],
        [mock_request.system_prompt],
        verbose=False,
    )

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.QUERY_RELEVANCE
    assert round(score.details.query_relevance.bert_f_score, 4) == expected_f_score
    assert score.prompt_tokens == 0
    assert score.completion_tokens == 0


@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_user_response_bertscore(mock_bert_model):
    # Arrange
    expected_f_score = 0.6568
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_f_score]),
    )

    scorer = ResponseBertScorer()
    mock_request = Mock(
        user_prompt="Test prompt",
        system_prompt="Test system prompt",
        llm_response="Test response",
    )

    # Act
    score = scorer.score(mock_request)

    # Assert
    mock_bert_model.return_value.score.assert_called_once_with(
        [mock_request.llm_response],
        [mock_request.system_prompt],
        verbose=False,
    )

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.RESPONSE_RELEVANCE
    assert round(score.details.response_relevance.bert_f_score, 4) == expected_f_score
    assert score.prompt_tokens == 0
    assert score.completion_tokens == 0


@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
def test_query_bert_scorer(mock_bert_model):
    # Mock the BERTScorer model and its score method
    mock_scorer = MagicMock()
    mock_bert_model.return_value = mock_scorer

    # Mock the score method to return the expected tensors
    # P, R, F scores as tensors
    p_scores = torch.tensor([0.8])
    r_scores = torch.tensor([0.7])
    f_scores = torch.tensor([0.75])

    mock_scorer.score.return_value = (p_scores, r_scores, f_scores)

    # Create scorer and request
    scorer = QueryBertScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
    )

    # Score the request
    result = scorer.score(request)

    # Verify the call
    mock_scorer.score.assert_called_once_with(
        ["What is the weather?"],
        ["You are a helpful weather assistant."],
        verbose=False,
    )

    # Verify the result
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.QUERY_RELEVANCE
    assert result.details.query_relevance.bert_f_score == 0.75
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0


@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
def test_response_bert_scorer(mock_bert_model):
    # Mock the BERTScorer model and its score method
    mock_scorer = MagicMock()
    mock_bert_model.return_value = mock_scorer

    # Mock the score method to return the expected tensors
    # P, R, F scores as tensors
    p_scores = torch.tensor([0.9])
    r_scores = torch.tensor([0.8])
    f_scores = torch.tensor([0.85])

    mock_scorer.score.return_value = (p_scores, r_scores, f_scores)

    # Create scorer and request
    scorer = ResponseBertScorer()
    request = MetricRequest(
        response="The weather is sunny and 75°F.",
        system_prompt="You are a helpful weather assistant.",
    )

    # Score the request
    result = scorer.score(request)

    # Verify the call
    mock_scorer.score.assert_called_once_with(
        ["The weather is sunny and 75°F."],
        ["You are a helpful weather assistant."],
        verbose=False,
    )

    # Verify the result
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.RESPONSE_RELEVANCE
    assert result.details.response_relevance.bert_f_score == 0.85
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0
