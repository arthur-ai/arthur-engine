from unittest.mock import patch
from uuid import uuid4

import pytest
from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.custom_exceptions import LLMContentFilterException, LLMExecutionException
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.hallucination.v2 import (
    HallucinationClaimsV2,
    LLMClaimResult,
    ReturnClaimFlags,
    get_claim_classifier_embedding_model,
)
from services.guardrails.judge_executor import JudgeCallResult, JudgeContext
from utils import constants

pytestmark = [pytest.mark.unit_tests, pytest.mark.xdist_group("ml_models")]

CLAIM_TEXT = "Isaac Newton built on the principles put forth by Galileo when formulating the laws of gravity."
CLAIM_REQUEST = ScoreRequest(
    rule_type=RuleType.MODEL_HALLUCINATION_V2,
    context="Some context",
    llm_response=CLAIM_TEXT,
)


@pytest.fixture
def claim_classifier_embedding_model():
    return get_claim_classifier_embedding_model()


@pytest.mark.parametrize("text", [CLAIM_TEXT, "1."])
@pytest.mark.parametrize(
    ("label", "expected", "message"),
    [
        ("0", RuleResultEnum.PASS, constants.HALLUCINATION_CLAIMS_VALID_MESSAGE),
        ("1", RuleResultEnum.FAIL, constants.HALLUCINATION_CLAIMS_INVALID_MESSAGE),
        (
            "0,0",
            RuleResultEnum.PARTIALLY_UNAVAILABLE,
            constants.HALLUCINATION_AT_LEAST_ONE_INDETERMINATE_LABEL_MESSAGE,
        ),
    ],
)
def test_claim_label_contract(
    claim_classifier_embedding_model, text, label, expected, message
):
    request = ScoreRequest(
        rule_type=RuleType.MODEL_HALLUCINATION_V2,
        context="Some context",
        llm_response=text,
    )
    response = JudgeCallResult(
        label, None, LLMTokenConsumption(prompt_tokens=10, completion_tokens=5)
    )
    with patch(
        "services.guardrails.judge_executor.JudgeEvaluation.complete",
        return_value=response,
    ):
        score = HallucinationClaimsV2(claim_classifier_embedding_model).score(request)
    assert score.result is expected
    assert message in score.details.message
    if expected == RuleResultEnum.PARTIALLY_UNAVAILABLE:
        assert all(
            claim.reason == constants.HALLUCINATION_INDETERMINATE_LABEL_MESSAGE
            for claim in score.details.claims
        )
    assert score.prompt_tokens == (20 if label == "1" else 10)


def test_claim_and_nonclaims_v2(claim_classifier_embedding_model):
    request = CLAIM_REQUEST.model_copy(
        update={
            "llm_response": CLAIM_TEXT
            + "\n\n- hello.\n- hi, how are you?\n- I'm fine thanks and you?"
        }
    )
    with patch(
        "services.guardrails.judge_executor.JudgeEvaluation.complete",
        return_value=JudgeCallResult(
            "0", None, LLMTokenConsumption(prompt_tokens=10, completion_tokens=5)
        ),
    ):
        score = HallucinationClaimsV2(claim_classifier_embedding_model).score(request)
    assert score.result is RuleResultEnum.PASS
    assert constants.HALLUCINATION_CLAIMS_VALID_MESSAGE in score.details.message
    assert (
        len(
            [
                claim
                for claim in score.details.claims
                if claim.reason == constants.HALLUCINATION_NONEVALUATION_EXPLANATION
            ]
        )
        == 3
    )
    assert score.details.claims[0].claim == CLAIM_TEXT


@pytest.mark.parametrize(
    "text",
    ["Hi!", "I don't have any information about that in the provided documents."],
)
def test_no_evaluable_claims_needs_no_judge(claim_classifier_embedding_model, text):
    request = CLAIM_REQUEST.model_copy(update={"llm_response": text})
    with patch(
        "services.guardrails.judge_executor.JudgeEvaluation.complete"
    ) as complete:
        score = HallucinationClaimsV2(claim_classifier_embedding_model).score(request)
    assert score.result is RuleResultEnum.PASS
    assert constants.HALLUCINATION_NO_CLAIMS_MESSAGE in score.details.message
    complete.assert_not_called()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            LLMExecutionException("untrusted provider detail"),
            constants.ERROR_DEFAULT_RULE_ENGINE,
        ),
        (
            LLMContentFilterException(),
            "GenAI Engine was unable to evaluate due to an upstream content policy",
        ),
    ],
)
def test_llm_execution_exception_handling_v2(
    claim_classifier_embedding_model, error, message
):
    with patch.object(HallucinationClaimsV2, "validate_claim_batch", side_effect=error):
        score = HallucinationClaimsV2(claim_classifier_embedding_model).score(
            CLAIM_REQUEST
        )
    assert score.result == RuleResultEnum.UNAVAILABLE
    assert score.details.message == message


@pytest.mark.parametrize(
    "labels",
    [
        [],
        [
            LLMClaimResult(
                claim_text=CLAIM_TEXT, is_hallucination=False, explanation="grounded"
            )
        ],
        [
            LLMClaimResult(
                claim_text=CLAIM_TEXT, is_hallucination=True, explanation="not grounded"
            )
        ],
    ],
)
def test_structured_output_contract(claim_classifier_embedding_model, labels):
    response = JudgeCallResult(
        "",
        ReturnClaimFlags(results=labels),
        LLMTokenConsumption(prompt_tokens=10, completion_tokens=5),
    )
    with patch(
        "services.guardrails.judge_executor.JudgeEvaluation.complete",
        return_value=response,
    ) as complete:
        score = HallucinationClaimsV2(claim_classifier_embedding_model).score(
            CLAIM_REQUEST,
            judge_context=JudgeContext(org_id=uuid4(), structured_output=True),
        )
    assert complete.call_args.args[2] is ReturnClaimFlags
    if not labels:
        assert score.result is RuleResultEnum.PARTIALLY_UNAVAILABLE
    else:
        assert score.result is (
            RuleResultEnum.FAIL if labels[0].is_hallucination else RuleResultEnum.PASS
        )
    assert score.prompt_tokens == 10
