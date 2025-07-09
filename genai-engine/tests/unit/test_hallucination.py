import os
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages.ai import AIMessage
from langchain_openai import AzureChatOpenAI
from schemas.custom_exceptions import LLMContentFilterException, LLMExecutionException
from schemas.enums import RuleResultEnum, RuleType
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.hallucination.v2 import (
    HallucinationClaimsV2,
    get_claim_classifier_embedding_model,
)
from utils import constants

os.environ[constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"
os.environ[constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"
os.environ[constants.GENAI_ENGINE_OPENAI_PROVIDER_ENV_VAR] = "Azure"


CLAIM_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_HALLUCINATION_V2,
    context="Some context",
    llm_response="Isaac Newton built on the principles put forth by Galileo when formulating the laws of gravity.",
)

SIMPLE_NUMERIC_CLAIM_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_HALLUCINATION_V2,
    context="What's 1x1 equal?",
    llm_response="1.",
)

CLAIM_REQUESTS = [CLAIM_REQUEST, SIMPLE_NUMERIC_CLAIM_REQUEST]

DIALOG_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_HALLUCINATION_V2,
    context="Some context",
    llm_response="Hi!",
)

NONCLAIM_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_HALLUCINATION_V2,
    context="Some context",
    llm_response="I don't have any information about that in the provided documents.",
)


@pytest.fixture
def claim_classifier_embedding_model():
    return get_claim_classifier_embedding_model()


@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(
    AzureChatOpenAI,
    "__init__",
    lambda *args, **kwargs: None,
)  # Bypassing GraderLLM's constructor
@pytest.mark.unit_tests
def test_all_claims_valid_v2(
    mock_llm_chain: MagicMock,
    claim_classifier_embedding_model,
):
    """Case where all claims are valid."""
    mock_llm_chain().invoke.return_value = AIMessage("0")

    scorer = HallucinationClaimsV2(claim_classifier_embedding_model)
    
    for request in CLAIM_REQUESTS:
        score = scorer.score(request)
        assert score.result is RuleResultEnum.PASS
        assert constants.HALLUCINATION_CLAIMS_VALID_MESSAGE in score.details.message


@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(
    AzureChatOpenAI,
    "__init__",
    lambda *args, **kwargs: None,
)  # Bypassing GraderLLM's constructor
@pytest.mark.unit_tests
def test_claim_and_nonclaims_v2(
    mock_llm_chain: MagicMock,
    claim_classifier_embedding_model,
):
    """Case where all claims are valid."""
    mock_llm_chain().invoke.return_value = AIMessage("0")
    request = ScoreRequest(
        rule_type=RuleType.MODEL_HALLUCINATION_V2,
        context="Some context",
        llm_response="""Isaac Newton built on the principles put forth by Galileo when formulating the laws of gravity.

    - hello. 
    - hi, how are you? 
    - I'm fine thanks and you?""",
    )

    scorer = HallucinationClaimsV2(claim_classifier_embedding_model)
    score = scorer.score(request)

    assert score.result is RuleResultEnum.PASS
    assert constants.HALLUCINATION_CLAIMS_VALID_MESSAGE in score.details.message
    assert (
        len(
            [
                claim
                for claim in score.details.claims
                if claim.reason == constants.HALLUCINATION_NONEVALUATION_EXPLANATION
            ],
        )
        == 3
    )


@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_some_claims_invalid_v2(
    mock_llm_chain: MagicMock,
    claim_classifier_embedding_model,
):
    """Case where some claims are invalid."""
    mock_llm_chain().invoke.return_value = AIMessage("1")

    scorer = HallucinationClaimsV2(claim_classifier_embedding_model)
    score = scorer.score(CLAIM_REQUEST)

    assert (
        score.result is RuleResultEnum.FAIL
        and constants.HALLUCINATION_CLAIMS_INVALID_MESSAGE in score.details.message
    )


@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_all_claims_invalid_v2(
    mock_llm_chain: MagicMock,
    claim_classifier_embedding_model,
):
    """Case where all claims are invalid."""
    mock_llm_chain().invoke.return_value = AIMessage("1")

    scorer = HallucinationClaimsV2(claim_classifier_embedding_model)
    score = scorer.score(CLAIM_REQUEST)

    assert (
        score.result is RuleResultEnum.FAIL
        and constants.HALLUCINATION_CLAIMS_INVALID_MESSAGE in score.details.message
    )


@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_all_dialog(mock_llm_chain: MagicMock, claim_classifier_embedding_model):
    """Case where an LLM is not making a claim because it is just giving dialog."""

    scorer = HallucinationClaimsV2(claim_classifier_embedding_model)
    score = scorer.score(DIALOG_REQUEST)

    assert (
        score.result is RuleResultEnum.PASS
        and constants.HALLUCINATION_NO_CLAIMS_MESSAGE in score.details.message
    )


@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_all_nonclaims(mock_llm_chain: MagicMock, claim_classifier_embedding_model):
    """Case where an LLM is not making a claim because it is saying it cannot answer"""

    scorer = HallucinationClaimsV2(claim_classifier_embedding_model)
    score = scorer.score(NONCLAIM_REQUEST)

    assert (
        score.result is RuleResultEnum.PASS
        and constants.HALLUCINATION_NO_CLAIMS_MESSAGE in score.details.message
    )


@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *args, **kwargs: None)
@pytest.mark.unit_tests
def test_claim_batch_mismatch(
    mock_llm_chain: MagicMock,
    claim_classifier_embedding_model,
):
    """Case where the LLM response returns a number of labels different from the number of claims"""
    mock_llm_chain().invoke.return_value = AIMessage("0,0")

    scorer = HallucinationClaimsV2(claim_classifier_embedding_model)
    score = scorer.score(CLAIM_REQUEST)

    assert score.result is RuleResultEnum.PARTIALLY_UNAVAILABLE and any(
        constants.HALLUCINATION_INDETERMINATE_LABEL_MESSAGE in c.reason
        for c in score.details.claims
    )


class LLMClientExecutionException:
    pass


@pytest.mark.unit_tests
def test_llm_execution_exception_handling_v2(claim_classifier_embedding_model):
    with mock.patch.object(
        HallucinationClaimsV2,
        "validate_claim_batch",
        side_effect=LLMExecutionException("test error"),
    ):
        hallucination_claims_v2 = HallucinationClaimsV2(
            claim_classifier_embedding_model,
        )
        rule_score = hallucination_claims_v2.score(CLAIM_REQUEST)

        assert rule_score.result == RuleResultEnum.UNAVAILABLE
        assert rule_score.details.message == "test error"

    with mock.patch.object(
        HallucinationClaimsV2,
        "validate_claim_batch",
        side_effect=LLMContentFilterException(),
    ):
        hallucination_claims_v2 = HallucinationClaimsV2(
            claim_classifier_embedding_model,
        )
        rule_score = hallucination_claims_v2.score(CLAIM_REQUEST)

        assert rule_score.result == RuleResultEnum.UNAVAILABLE
        assert (
            rule_score.details.message
            == "GenAI Engine was unable to evaluate due to an upstream content policy"
        )
