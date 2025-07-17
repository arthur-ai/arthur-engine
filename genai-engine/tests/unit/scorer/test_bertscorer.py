import os
from unittest.mock import MagicMock, Mock, patch

import pytest
import torch
from langchain.chat_models import AzureChatOpenAI

from schemas.common_schemas import LLMTokenConsumption
from schemas.enums import MetricType
from schemas.internal_schemas import MetricResult
from schemas.metric_schemas import MetricRequest
from scorer.metrics.relevance.relevance import (
    QueryBertScorer,
    ResponseBertScorer,
    ResponseRelevanceScorer,
    UserQueryRelevanceScorer,
)
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
    expected_f_score = 0.66
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_f_score]),
    )

    scorer = QueryBertScorer()
    mock_request = Mock(user_query="Test prompt", system_prompt="Test system prompt")

    # Act
    score = scorer.score(mock_request)

    # Assert
    mock_bert_model.return_value.score.assert_called_once_with(
        [mock_request.user_query],
        [mock_request.system_prompt],
        verbose=False,
    )

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.QUERY_RELEVANCE
    assert score.details.query_relevance.bert_f_score == expected_f_score
    assert score.prompt_tokens == 0
    assert score.completion_tokens == 0


@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_user_response_bertscore(mock_bert_model):
    # Arrange
    expected_f_score = 0.66
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_f_score]),
    )

    scorer = ResponseBertScorer()
    mock_request = Mock(
        user_query="Test prompt",
        system_prompt="Test system prompt",
        response="Test response",
    )

    # Act
    score = scorer.score(mock_request)

    # Assert
    mock_bert_model.return_value.score.assert_called_once_with(
        [mock_request.response],
        [mock_request.system_prompt],
        verbose=False,
    )

    assert isinstance(score, MetricResult)
    assert score.metric_type == MetricType.RESPONSE_RELEVANCE
    assert score.details.response_relevance.bert_f_score == expected_f_score
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


@patch("scorer.metrics.relevance.relevance.get_llm_executor")
@patch("scorer.metrics.relevance.relevance.get_relevance_reranker")
@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@pytest.mark.unit_tests
def test_user_query_relevance_scorer_structured_outputs(
    mock_bert_model,
    mock_reranker,
    mock_llm_executor,
):
    """Test UserQueryRelevanceScorer with structured outputs enabled"""
    # Arrange
    expected_bert_f_score = 0.75
    expected_reranker_score = 0.85
    expected_llm_score = 0.9

    # Mock BertScorer
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_bert_f_score]),
    )

    # Mock reranker
    mock_reranker.return_value.return_value = {"score": expected_reranker_score}

    # Mock LLM executor - supports structured outputs
    mock_llm_executor.return_value.supports_structured_outputs.return_value = True
    mock_llm_executor.return_value.execute.return_value = (
        {
            "relevance_score": expected_llm_score,
            "justification": "Test justification",
            "suggested_refinement": "Test refinement",
        },
        LLMTokenConsumption(prompt_tokens=100, completion_tokens=50),
    )

    # Create scorer and request
    scorer = UserQueryRelevanceScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
    )
    config = {"use_llm_judge": True}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.QUERY_RELEVANCE
    assert result.details.query_relevance.bert_f_score == expected_bert_f_score
    assert (
        result.details.query_relevance.reranker_relevance_score
        == expected_reranker_score
    )
    assert result.details.query_relevance.llm_relevance_score == expected_llm_score
    assert result.details.query_relevance.reason == "Test justification"
    assert result.details.query_relevance.refinement == "Test refinement"
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50


@patch("scorer.metrics.relevance.relevance.get_llm_executor")
@patch("scorer.metrics.relevance.relevance.get_relevance_reranker")
@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@pytest.mark.unit_tests
def test_user_query_relevance_scorer_legacy_outputs(
    mock_bert_model,
    mock_reranker,
    mock_llm_executor,
):
    """Test UserQueryRelevanceScorer with legacy/unstructured outputs"""
    # Arrange
    expected_bert_f_score = 0.65
    expected_reranker_score = 0.75
    expected_llm_score = 0.8

    # Mock BertScorer
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_bert_f_score]),
    )

    # Mock reranker
    mock_reranker.return_value.return_value = {"score": expected_reranker_score}

    # Mock LLM executor - does NOT support structured outputs
    mock_llm_executor.return_value.supports_structured_outputs.return_value = False
    mock_llm_executor.return_value.execute.return_value = (
        {
            "relevance_score": expected_llm_score,
            "justification": "Legacy justification",
            "suggested_refinement": "Legacy refinement",
        },
        LLMTokenConsumption(prompt_tokens=120, completion_tokens=60),
    )

    # Create scorer and request
    scorer = UserQueryRelevanceScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
    )
    config = {"use_llm_judge": True}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.QUERY_RELEVANCE
    assert result.details.query_relevance.bert_f_score == expected_bert_f_score
    assert (
        result.details.query_relevance.reranker_relevance_score
        == expected_reranker_score
    )
    assert result.details.query_relevance.llm_relevance_score == expected_llm_score
    assert result.details.query_relevance.reason == "Legacy justification"
    assert result.details.query_relevance.refinement == "Legacy refinement"
    assert result.prompt_tokens == 120
    assert result.completion_tokens == 60


@patch("scorer.metrics.relevance.relevance.get_llm_executor")
@patch("scorer.metrics.relevance.relevance.get_relevance_reranker")
@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@pytest.mark.unit_tests
def test_response_relevance_scorer_structured_outputs(
    mock_bert_model,
    mock_reranker,
    mock_llm_executor,
):
    """Test ResponseRelevanceScorer with structured outputs enabled"""
    # Arrange
    expected_bert_f_score = 0.8
    expected_reranker_score = 0.9
    expected_llm_score = 0.95

    # Mock BertScorer
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_bert_f_score]),
    )

    # Mock reranker
    mock_reranker.return_value.return_value = {"score": expected_reranker_score}

    # Mock LLM executor - supports structured outputs
    mock_llm_executor.return_value.supports_structured_outputs.return_value = True
    mock_llm_executor.return_value.execute.return_value = (
        {
            "relevance_score": expected_llm_score,
            "justification": "Response is highly relevant",
            "suggested_refinement": "No refinement needed",
        },
        LLMTokenConsumption(prompt_tokens=150, completion_tokens=75),
    )

    # Create scorer and request
    scorer = ResponseRelevanceScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
        response="The weather is sunny and 75°F.",
    )
    config = {"use_llm_judge": True}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.RESPONSE_RELEVANCE
    assert result.details.response_relevance.bert_f_score == expected_bert_f_score
    assert (
        result.details.response_relevance.reranker_relevance_score
        == expected_reranker_score
    )
    assert result.details.response_relevance.llm_relevance_score == expected_llm_score
    assert result.details.response_relevance.reason == "Response is highly relevant"
    assert result.details.response_relevance.refinement == "No refinement needed"
    assert result.prompt_tokens == 150
    assert result.completion_tokens == 75


@patch("scorer.metrics.relevance.relevance.get_llm_executor")
@patch("scorer.metrics.relevance.relevance.get_relevance_reranker")
@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@pytest.mark.unit_tests
def test_response_relevance_scorer_legacy_outputs(
    mock_bert_model,
    mock_reranker,
    mock_llm_executor,
):
    """Test ResponseRelevanceScorer with legacy/unstructured outputs"""
    # Arrange
    expected_bert_f_score = 0.7
    expected_reranker_score = 0.8
    expected_llm_score = 0.85

    # Mock BertScorer
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_bert_f_score]),
    )

    # Mock reranker
    mock_reranker.return_value.return_value = {"score": expected_reranker_score}

    # Mock LLM executor - does NOT support structured outputs
    mock_llm_executor.return_value.supports_structured_outputs.return_value = False
    mock_llm_executor.return_value.execute.return_value = (
        {
            "relevance_score": expected_llm_score,
            "justification": "Response is mostly relevant",
            "suggested_refinement": "Could be more specific",
        },
        LLMTokenConsumption(prompt_tokens=140, completion_tokens=70),
    )

    # Create scorer and request
    scorer = ResponseRelevanceScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
        response="The weather is nice today.",
    )
    config = {"use_llm_judge": True}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.RESPONSE_RELEVANCE
    assert result.details.response_relevance.bert_f_score == expected_bert_f_score
    assert (
        result.details.response_relevance.reranker_relevance_score
        == expected_reranker_score
    )
    assert result.details.response_relevance.llm_relevance_score == expected_llm_score
    assert result.details.response_relevance.reason == "Response is mostly relevant"
    assert result.details.response_relevance.refinement == "Could be more specific"
    assert result.prompt_tokens == 140
    assert result.completion_tokens == 70


@patch("scorer.metrics.relevance.relevance.get_llm_executor")
@patch("scorer.metrics.relevance.relevance.get_relevance_reranker")
@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@pytest.mark.unit_tests
def test_user_query_relevance_scorer_without_llm_judge(
    mock_bert_model,
    mock_reranker,
    mock_llm_executor,
):
    """Test UserQueryRelevanceScorer without LLM judge (only bert and reranker)"""
    # Arrange
    expected_bert_f_score = 0.6
    expected_reranker_score = 0.7

    # Mock BertScorer
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_bert_f_score]),
    )

    # Mock reranker
    mock_reranker.return_value.return_value = {"score": expected_reranker_score}

    # Create scorer and request
    scorer = UserQueryRelevanceScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
    )
    config = {"use_llm_judge": False}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.QUERY_RELEVANCE
    assert result.details.query_relevance.bert_f_score == expected_bert_f_score
    assert (
        result.details.query_relevance.reranker_relevance_score
        == expected_reranker_score
    )
    assert result.details.query_relevance.llm_relevance_score == 0
    assert result.details.query_relevance.reason is None
    assert result.details.query_relevance.refinement is None
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0


@patch("scorer.metrics.relevance.relevance.get_llm_executor")
@patch("scorer.metrics.relevance.relevance.get_relevance_reranker")
@patch("scorer.metrics.relevance.relevance.get_bert_scorer_model")
@pytest.mark.unit_tests
def test_response_relevance_scorer_without_llm_judge(
    mock_bert_model,
    mock_reranker,
    mock_llm_executor,
):
    """Test ResponseRelevanceScorer without LLM judge (only bert and reranker)"""
    # Arrange
    expected_bert_f_score = 0.65
    expected_reranker_score = 0.75

    # Mock BertScorer
    mock_bert_model.return_value.score.return_value = (
        None,
        None,
        torch.tensor([expected_bert_f_score]),
    )

    # Mock reranker
    mock_reranker.return_value.return_value = {"score": expected_reranker_score}

    # Create scorer and request
    scorer = ResponseRelevanceScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
        response="The weather is sunny and 75°F.",
    )
    config = {"use_llm_judge": False}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.RESPONSE_RELEVANCE
    assert result.details.response_relevance.bert_f_score == expected_bert_f_score
    assert (
        result.details.response_relevance.reranker_relevance_score
        == expected_reranker_score
    )
    assert result.details.response_relevance.llm_relevance_score == 0
    assert result.details.response_relevance.reason is None
    assert result.details.response_relevance.refinement is None
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0
