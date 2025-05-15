import os
from unittest.mock import Mock, patch

import pytest
import torch
from langchain.chat_models import AzureChatOpenAI
from schemas.enums import MetricType
from schemas.metric_schemas import MetricScore
from scorer.metrics.relevance.relevance import QueryBertScorer, ResponseBertScorer
from utils import utils

os.environ[utils.constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"
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

    assert isinstance(score, MetricScore)
    assert score.metric == MetricType.QUERY_RELEVANCE
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

    assert isinstance(score, MetricScore)
    assert score.metric == MetricType.RESPONSE_RELEVANCE
    assert round(score.details.response_relevance.bert_f_score, 4) == expected_f_score
    assert score.prompt_tokens == 0
    assert score.completion_tokens == 0 