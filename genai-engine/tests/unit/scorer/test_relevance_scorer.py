import os
from unittest.mock import patch

import pytest
import torch

from schemas.common_schemas import LLMTokenConsumption
from schemas.enums import MetricType
from schemas.internal_schemas import MetricResult
from schemas.metric_schemas import MetricRequest
from scorer.metrics.relevance.relevance import (
    ResponseRelevanceScorer,
    UserQueryRelevanceScorer,
    round_score,
)
from utils import utils

os.environ[utils.constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = (
    "1::2/::3"
)
os.environ[utils.constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"


@pytest.fixture
def mock_models():
    """Common mock setup for models"""
    with (
        patch("scorer.metrics.relevance.relevance.get_bert_scorer") as mock_bert,
        patch(
            "scorer.metrics.relevance.relevance.get_relevance_reranker",
        ) as mock_reranker,
        patch("scorer.metrics.relevance.relevance.get_llm_executor") as mock_llm,
        patch(
            "scorer.metrics.relevance.relevance.relevance_models_enabled",
        ) as mock_enabled,
    ):

        # Default mock setup
        mock_enabled.return_value = True
        mock_bert.return_value.score.return_value = (None, None, torch.tensor([0.75]))
        mock_reranker.return_value.return_value = {"score": 0.85}
        mock_llm.return_value.supports_structured_outputs.return_value = True
        mock_llm.return_value.execute.return_value = (
            {
                "relevance_score": 0.9,
                "justification": "Test justification",
                "suggested_refinement": "Test refinement",
            },
            LLMTokenConsumption(prompt_tokens=100, completion_tokens=50),
        )

        yield {
            "bert": mock_bert,
            "reranker": mock_reranker,
            "llm": mock_llm,
            "enabled": mock_enabled,
        }


# Relevance Scorer Tests
@pytest.mark.parametrize(
    "scorer_class,metric_type,request_data,expected_detail_field",
    [
        (
            UserQueryRelevanceScorer,
            MetricType.QUERY_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
            },
            "query_relevance",
        ),
        (
            ResponseRelevanceScorer,
            MetricType.RESPONSE_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
                "response": "The weather is sunny and 75°F.",
            },
            "response_relevance",
        ),
    ],
)
def test_relevance_scorer_full_pipeline(
    mock_models,
    scorer_class,
    metric_type,
    request_data,
    expected_detail_field,
):
    """Test full pipeline with all components enabled"""
    # Arrange
    scorer = scorer_class()
    request = MetricRequest(**request_data)
    config = {"use_llm_judge": True}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50

    # Check all scores are present
    details = getattr(result.details, expected_detail_field)
    assert details.bert_f_score == 0.75
    assert details.reranker_relevance_score == 0.85
    assert details.llm_relevance_score == 0.9
    assert details.reason == "Test justification"
    assert details.refinement == "Test refinement"


@pytest.mark.parametrize(
    "scorer_class,metric_type,request_data,expected_detail_field",
    [
        (
            UserQueryRelevanceScorer,
            MetricType.QUERY_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
            },
            "query_relevance",
        ),
        (
            ResponseRelevanceScorer,
            MetricType.RESPONSE_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
                "response": "The weather is sunny and 75°F.",
            },
            "response_relevance",
        ),
    ],
)
def test_relevance_scorer_without_llm_judge(
    mock_models,
    scorer_class,
    metric_type,
    request_data,
    expected_detail_field,
):
    """Test scoring without LLM judge"""
    # Arrange
    scorer = scorer_class()
    request = MetricRequest(**request_data)
    config = {"use_llm_judge": False}

    # Act
    result = scorer.score(request, config)

    # Assert
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0

    # Check only model scores are present
    details = getattr(result.details, expected_detail_field)
    assert details.bert_f_score == 0.75
    assert details.reranker_relevance_score == 0.85
    assert details.llm_relevance_score is None
    assert details.reason is None
    assert details.refinement is None


@pytest.mark.parametrize(
    "scorer_class,metric_type,request_data,expected_detail_field",
    [
        (
            UserQueryRelevanceScorer,
            MetricType.QUERY_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
            },
            "query_relevance",
        ),
        (
            ResponseRelevanceScorer,
            MetricType.RESPONSE_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
                "response": "The weather is sunny and 75°F.",
            },
            "response_relevance",
        ),
    ],
)
def test_relevance_scorer_models_disabled(
    mock_models,
    scorer_class,
    metric_type,
    request_data,
    expected_detail_field,
):
    """Test scoring when models are disabled"""
    # Arrange
    mock_models["enabled"].return_value = False
    scorer = scorer_class()
    request = MetricRequest(**request_data)
    config = {"use_llm_judge": False}

    # Act
    result = scorer.score(request, config)

    # Assert - should return all None values
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0

    details = getattr(result.details, expected_detail_field)
    assert details.bert_f_score is None
    assert details.reranker_relevance_score is None
    assert details.llm_relevance_score is None
    assert details.reason is None
    assert details.refinement is None


@pytest.mark.parametrize(
    "scorer_class,metric_type,request_data,expected_detail_field",
    [
        (
            UserQueryRelevanceScorer,
            MetricType.QUERY_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
            },
            "query_relevance",
        ),
        (
            ResponseRelevanceScorer,
            MetricType.RESPONSE_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
                "response": "The weather is sunny and 75°F.",
            },
            "response_relevance",
        ),
    ],
)
def test_relevance_scorer_models_disabled_with_llm_judge(
    mock_models,
    scorer_class,
    metric_type,
    request_data,
    expected_detail_field,
):
    """Test scoring when models are disabled but LLM judge is enabled"""
    # Arrange
    mock_models["enabled"].return_value = False
    scorer = scorer_class()
    request = MetricRequest(**request_data)
    config = {"use_llm_judge": True}

    # Act
    result = scorer.score(request, config)

    # Assert - should have LLM score but None for model scores
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50

    details = getattr(result.details, expected_detail_field)
    assert details.bert_f_score is None
    assert details.reranker_relevance_score is None
    assert details.llm_relevance_score == 0.9
    assert details.reason == "Test justification"
    assert details.refinement == "Test refinement"


@pytest.mark.parametrize(
    "scorer_class,metric_type,request_data,expected_detail_field",
    [
        (
            UserQueryRelevanceScorer,
            MetricType.QUERY_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
            },
            "query_relevance",
        ),
        (
            ResponseRelevanceScorer,
            MetricType.RESPONSE_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
                "response": "The weather is sunny and 75°F.",
            },
            "response_relevance",
        ),
    ],
)
def test_relevance_scorer_llm_error_handling(
    mock_models,
    scorer_class,
    metric_type,
    request_data,
    expected_detail_field,
):
    """Test error handling when LLM judge encounters an error"""
    # Arrange
    mock_models["llm"].return_value.execute.side_effect = Exception("LLM API Error")
    scorer = scorer_class()
    request = MetricRequest(**request_data)
    config = {"use_llm_judge": True}

    # Act
    result = scorer.score(request, config)

    # Assert - should return model scores but handle LLM error gracefully
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0

    details = getattr(result.details, expected_detail_field)
    assert details.bert_f_score == 0.75
    assert details.reranker_relevance_score == 0.85
    assert details.llm_relevance_score is None
    assert details.reason is None
    assert details.refinement is None


@pytest.mark.parametrize(
    "scorer_class,metric_type,request_data,expected_detail_field",
    [
        (
            UserQueryRelevanceScorer,
            MetricType.QUERY_RELEVANCE,
            {"user_query": "", "system_prompt": ""},
            "query_relevance",
        ),
        (
            ResponseRelevanceScorer,
            MetricType.RESPONSE_RELEVANCE,
            {"user_query": "", "system_prompt": "", "response": ""},
            "response_relevance",
        ),
    ],
)
def test_relevance_scorer_empty_inputs(
    mock_models,
    scorer_class,
    metric_type,
    request_data,
    expected_detail_field,
):
    """Test handling of empty inputs"""
    # Arrange
    mock_models["bert"].return_value.score.return_value = (
        None,
        None,
        torch.tensor([0.0]),
    )
    mock_models["reranker"].return_value.return_value = {"score": 0.0}

    scorer = scorer_class()
    request = MetricRequest(**request_data)
    config = {"use_llm_judge": False}

    # Act
    result = scorer.score(request, config)

    # Assert - should handle empty inputs gracefully
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type

    details = getattr(result.details, expected_detail_field)
    assert details.bert_f_score == 0.0
    assert details.reranker_relevance_score == 0.0


@pytest.mark.parametrize(
    "scorer_class,metric_type,request_data,expected_detail_field",
    [
        (
            UserQueryRelevanceScorer,
            MetricType.QUERY_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
            },
            "query_relevance",
        ),
        (
            ResponseRelevanceScorer,
            MetricType.RESPONSE_RELEVANCE,
            {
                "user_query": "What is the weather?",
                "system_prompt": "You are a helpful weather assistant.",
                "response": "The weather is sunny and 75°F.",
            },
            "response_relevance",
        ),
    ],
)
def test_relevance_scorer_chain_selection(
    mock_models,
    scorer_class,
    metric_type,
    request_data,
    expected_detail_field,
):
    """Test chain selection logic for structured vs legacy outputs"""
    # Arrange
    scorer = scorer_class()
    request = MetricRequest(**request_data)
    config = {"use_llm_judge": True}

    # Test structured outputs
    mock_models["llm"].return_value.supports_structured_outputs.return_value = True
    result = scorer.score(request, config)
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type

    # Test legacy outputs
    mock_models["llm"].return_value.supports_structured_outputs.return_value = False
    result = scorer.score(request, config)
    assert isinstance(result, MetricResult)
    assert result.metric_type == metric_type


def test_relevance_scorer_config_defaults(mock_models):
    """Test default config behavior"""
    # Arrange
    scorer = UserQueryRelevanceScorer()
    request = MetricRequest(
        user_query="What is the weather?",
        system_prompt="You are a helpful weather assistant.",
    )

    # Act - no config provided, should default to use_llm_judge=True
    result = scorer.score(request, {})

    # Assert - should use LLM judge by default
    assert isinstance(result, MetricResult)
    assert result.metric_type == MetricType.QUERY_RELEVANCE


# Round Score Tests
@pytest.mark.parametrize(
    "input_score,expected_output",
    [
        (0.123456, 0.123),
        (0.987654, 0.988),
        (0.5, 0.5),
        (1.0, 1.0),
        (0.0, 0.0),
        (0.999, 0.999),
        (0.001, 0.001),
        ("0.75", 0.75),
        ("0.123456", 0.123),
    ],
)
def test_round_score_function(input_score, expected_output):
    """Test the round_score function for consistent precision"""
    assert round_score(input_score) == expected_output


# Model Loading Tests
@patch("utils.model_load.relevance_models_enabled")
@patch("utils.model_load.BERTScorer")
def test_get_bert_scorer_disabled(mock_bert_scorer, mock_relevance_models_enabled):
    """Test get_bert_scorer when relevance models are disabled"""
    from utils.model_load import get_bert_scorer

    # Arrange - models disabled
    mock_relevance_models_enabled.return_value = False

    # Act
    result = get_bert_scorer()

    # Assert - should return None
    assert result is None
    mock_bert_scorer.assert_not_called()


@patch("utils.model_load.relevance_models_enabled")
@patch("utils.model_load.TextClassificationPipeline")
@patch("utils.model_load.get_relevance_model")
@patch("utils.model_load.get_relevance_tokenizer")
def test_get_relevance_reranker_disabled(
    mock_get_tokenizer,
    mock_get_model,
    mock_pipeline,
    mock_relevance_models_enabled,
):
    """Test get_relevance_reranker when relevance models are disabled"""
    from utils.model_load import get_relevance_reranker

    # Arrange - models disabled
    mock_relevance_models_enabled.return_value = False

    # Act
    result = get_relevance_reranker()

    # Assert - should return None
    assert result is None
    mock_get_model.assert_not_called()
    mock_get_tokenizer.assert_not_called()
    mock_pipeline.assert_not_called()
