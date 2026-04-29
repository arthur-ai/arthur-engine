"""HallucinationClaimsV2 wire + LLM judge tests.

The claim filter (sentence-transformer + logreg) lives in the models
service now — see arthur-engine/models-service/tests/unit/test_claim_filter.py.

These engine-side tests exercise the judge orchestration:
- Use FakeModelsServiceClient to force CLAIM/NONCLAIM/DIALOG labels on inputs.
- Mock get_llm_executor and the langchain RunnableSequence the same way the
  pre-extraction tests did.
"""

import os
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import RuleResultEnum, RuleType
from langchain_core.messages.ai import AIMessage
from langchain_openai import AzureChatOpenAI

from schemas.custom_exceptions import LLMContentFilterException, LLMExecutionException
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.hallucination.v2 import HallucinationClaimsV2
from tests.conftest import make_claim_filter_response
from utils import constants

os.environ[constants.GENAI_ENGINE_OPENAI_EMBEDDINGS_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"
os.environ[constants.GENAI_ENGINE_OPENAI_GPT_ENDPOINTS_KEYS_ENV_VAR] = "1::2/::3"
os.environ[constants.GENAI_ENGINE_OPENAI_PROVIDER_ENV_VAR] = "Azure"


CLAIM_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_HALLUCINATION_V2,
    context="Some context",
    llm_response="Isaac Newton built on the principles put forth by Galileo when formulating the laws of gravity.",
)

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


def _label_all_as(client, request: ScoreRequest, label: str) -> None:
    """Helper: set the fake claim_filter response so every parsed claim from
    `request.llm_response` is labeled `label`."""
    from utils.claim_parser import ClaimParser

    parsed = ClaimParser().process_and_extract_claims(request.llm_response)
    client.claim_filter_response = make_claim_filter_response(
        *((text, label, 0.99) for text in parsed),
    )


def _judge_returns(mock_get_llm_executor, ai_message_value: str) -> None:
    """Wire up the LLM-executor mock so .execute returns the given AIMessage."""
    mock_get_llm_executor.return_value.get_gpt_model.return_value = MagicMock()
    mock_get_llm_executor.return_value.supports_structured_outputs.return_value = False
    mock_get_llm_executor.return_value.execute.return_value = (
        AIMessage(ai_message_value),
        LLMTokenConsumption(prompt_tokens=10, completion_tokens=5),
    )


# ---------------------------------------------------------------------------


@patch("scorer.checks.hallucination.v2.get_llm_executor")
@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *a, **kw: None)
@pytest.mark.unit_tests
def test_all_claims_valid(mock_llm_chain, mock_get_llm_executor, fake_models_client):
    mock_llm_chain().invoke.return_value = AIMessage("0")
    _judge_returns(mock_get_llm_executor, "0")
    _label_all_as(fake_models_client, CLAIM_REQUEST, "claim")

    scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
    score = scorer.score(CLAIM_REQUEST)

    assert score.result == RuleResultEnum.PASS
    assert constants.HALLUCINATION_CLAIMS_VALID_MESSAGE in score.details.message


@patch("scorer.checks.hallucination.v2.get_llm_executor")
@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *a, **kw: None)
@pytest.mark.unit_tests
def test_all_claims_invalid(mock_llm_chain, mock_get_llm_executor, fake_models_client):
    mock_llm_chain().invoke.return_value = AIMessage("1")
    _judge_returns(mock_get_llm_executor, "1")
    _label_all_as(fake_models_client, CLAIM_REQUEST, "claim")

    scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
    score = scorer.score(CLAIM_REQUEST)

    assert score.result == RuleResultEnum.FAIL
    assert constants.HALLUCINATION_CLAIMS_INVALID_MESSAGE in score.details.message


@patch("scorer.checks.hallucination.v2.get_llm_executor")
@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *a, **kw: None)
@pytest.mark.unit_tests
def test_all_dialog_skips_judge(mock_llm_chain, mock_get_llm_executor, fake_models_client):
    """When everything classifies as DIALOG, no claims hit the LLM judge."""
    _judge_returns(mock_get_llm_executor, "0")
    _label_all_as(fake_models_client, DIALOG_REQUEST, "dialog")

    scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
    score = scorer.score(DIALOG_REQUEST)

    assert score.result == RuleResultEnum.PASS
    assert constants.HALLUCINATION_NO_CLAIMS_MESSAGE in score.details.message


@patch("scorer.checks.hallucination.v2.get_llm_executor")
@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *a, **kw: None)
@pytest.mark.unit_tests
def test_all_nonclaims_skips_judge(mock_llm_chain, mock_get_llm_executor, fake_models_client):
    _judge_returns(mock_get_llm_executor, "0")
    _label_all_as(fake_models_client, NONCLAIM_REQUEST, "nonclaim")

    scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
    score = scorer.score(NONCLAIM_REQUEST)

    assert score.result == RuleResultEnum.PASS
    assert constants.HALLUCINATION_NO_CLAIMS_MESSAGE in score.details.message


@patch("scorer.checks.hallucination.v2.get_llm_executor")
@patch("langchain_core.runnables.base.RunnableSequence")
@patch.object(AzureChatOpenAI, "__init__", lambda *a, **kw: None)
@pytest.mark.unit_tests
def test_claim_batch_mismatch(mock_llm_chain, mock_get_llm_executor, fake_models_client):
    """LLM judge returns more labels than claims → PARTIALLY_UNAVAILABLE."""
    mock_llm_chain().invoke.return_value = AIMessage("0,0")
    _judge_returns(mock_get_llm_executor, "0,0")
    _label_all_as(fake_models_client, CLAIM_REQUEST, "claim")

    scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
    score = scorer.score(CLAIM_REQUEST)

    assert score.result == RuleResultEnum.PARTIALLY_UNAVAILABLE
    assert any(
        constants.HALLUCINATION_INDETERMINATE_LABEL_MESSAGE in c.reason
        for c in score.details.claims
    )


@patch("scorer.checks.hallucination.v2.get_llm_executor")
@patch.object(AzureChatOpenAI, "__init__", lambda *a, **kw: None)
@pytest.mark.unit_tests
def test_llm_execution_exception(mock_get_llm_executor, fake_models_client):
    _judge_returns(mock_get_llm_executor, "0")
    _label_all_as(fake_models_client, CLAIM_REQUEST, "claim")

    with mock.patch.object(
        HallucinationClaimsV2,
        "validate_claim_batch",
        side_effect=LLMExecutionException("test error"),
    ):
        scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
        score = scorer.score(CLAIM_REQUEST)
        assert score.result == RuleResultEnum.UNAVAILABLE
        assert score.details.message == "test error"

    with mock.patch.object(
        HallucinationClaimsV2,
        "validate_claim_batch",
        side_effect=LLMContentFilterException(),
    ):
        scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
        score = scorer.score(CLAIM_REQUEST)
        assert score.result == RuleResultEnum.UNAVAILABLE


@patch("scorer.checks.hallucination.v2.get_llm_executor")
@patch.object(AzureChatOpenAI, "__init__", lambda *a, **kw: None)
@pytest.mark.unit_tests
def test_claim_filter_unavailable(mock_get_llm_executor, fake_models_client):
    """If the models service is down, the scorer returns MODEL_NOT_AVAILABLE
    without ever calling the LLM judge."""
    from clients.models_service_client import ModelNotAvailableError

    _judge_returns(mock_get_llm_executor, "0")

    def boom(texts):
        raise ModelNotAvailableError("simulated")

    fake_models_client.claim_filter = boom  # type: ignore[method-assign]

    scorer = HallucinationClaimsV2(models_service_client=fake_models_client)
    score = scorer.score(CLAIM_REQUEST)
    assert score.result == RuleResultEnum.MODEL_NOT_AVAILABLE
    mock_get_llm_executor.return_value.execute.assert_not_called()
