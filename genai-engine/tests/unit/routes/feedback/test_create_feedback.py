from datetime import datetime
from typing import Generator
from uuid import uuid4

import pytest
from arthur_common.models.enums import InferenceFeedbackTarget, RuleResultEnum
from sqlalchemy.orm import Session

from db_models import (
    DatabaseInference,
    DatabaseInferenceFeedback,
    DatabaseInferencePrompt,
    DatabaseInferencePromptContent,
    DatabaseInferenceResponse,
    DatabaseInferenceResponseContent,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.unit.routes.feedback import FEEDBACK_DB_SESSION


@pytest.fixture(scope="module", autouse=True)
def setup_create_feedback_tests() -> Generator[str, None, None]:
    db_session = FEEDBACK_DB_SESSION
    test_create_feedback_prompt_id = str(uuid4())
    test_create_feedback_response_id = str(uuid4())
    test_create_feedback_inference_id = str(uuid4())
    inference_id = str(uuid4())
    initialize_test_create_feedback_inference(
        db_session,
        test_create_feedback_prompt_id,
        test_create_feedback_response_id,
        test_create_feedback_inference_id,
        inference_id,
    )
    yield test_create_feedback_inference_id
    cleanup_create_feedback_test_data(db_session, test_create_feedback_inference_id)


def initialize_test_create_feedback_inference(
    db_session: Session,
    test_create_feedback_prompt_id: str,
    test_create_feedback_response_id: str,
    test_create_feedback_inference_id: str,
    inference_id: str,
) -> None:
    db_session.begin()
    db_prompt = DatabaseInferencePrompt(
        id=test_create_feedback_prompt_id,
        inference_id=test_create_feedback_inference_id,
        result=RuleResultEnum.PASS.value,
        content=DatabaseInferencePromptContent(
            inference_prompt_id=test_create_feedback_prompt_id,
            content=f"test_create_feedback_prompt_message",
        ),
        prompt_rule_results=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_response = DatabaseInferenceResponse(
        id=test_create_feedback_response_id,
        inference_id=test_create_feedback_inference_id,
        result=RuleResultEnum.PASS.value,
        content=DatabaseInferenceResponseContent(
            inference_response_id=test_create_feedback_prompt_id,
            content=f"test_create_feedback_response_message",
        ),
        response_rule_results=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_inference = DatabaseInference(
        id=inference_id,
        result=RuleResultEnum.PASS.value,
        inference_prompt=db_prompt,
        inference_response=db_response,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(db_inference)
    db_session.commit()


def cleanup_create_feedback_test_data(
    db_session: Session,
    test_create_feedback_inference_id: str,
) -> None:
    db_session.begin()
    db_session.query(DatabaseInferenceFeedback).where(
        DatabaseInferenceFeedback.inference_id.in_(
            [test_create_feedback_inference_id],
        ),
    ).delete()  # cleanup feedback
    db_session.query(DatabaseInferenceResponse).where(
        DatabaseInferenceResponse.inference_id.in_(
            [test_create_feedback_inference_id],
        ),
    ).delete()  # cleanup response
    db_session.query(DatabaseInferencePrompt).where(
        DatabaseInferencePrompt.inference_id.in_([test_create_feedback_inference_id]),
    ).delete()  # cleanup prompt
    db_session.query(DatabaseInference).where(
        DatabaseInference.id.in_([test_create_feedback_inference_id]),
    ).delete()  # cleanup inference
    db_session.commit()


@pytest.mark.parametrize(
    "target,score,reason,user_id,expected_response_code",
    [
        pytest.param(
            InferenceFeedbackTarget.CONTEXT,
            -1,
            "test reason 1",
            "user_id",
            201,
            id="context feedback",
        ),
        pytest.param(
            InferenceFeedbackTarget.RESPONSE_RESULTS,
            0,
            "test reason 2",
            "user_id",
            201,
            id="response feedback",
        ),
        pytest.param(
            InferenceFeedbackTarget.PROMPT_RESULTS,
            1,
            "test reason 3",
            "user_id",
            201,
            id="prompt feedback",
        ),
        pytest.param(
            InferenceFeedbackTarget.CONTEXT,
            0,
            None,
            "user_id",
            201,
            id="no reason",
        ),
        pytest.param(
            InferenceFeedbackTarget.CONTEXT,
            -1,
            "test reason 1",
            None,
            201,
            id="no user_id",
        ),
    ],
)
@pytest.mark.unit_tests
def test_create_feedback(
    target: InferenceFeedbackTarget,
    score: int,
    reason: str | None,
    user_id: str | None,
    expected_response_code: int,
    client: GenaiEngineTestClientBase,
    setup_create_feedback_tests: str,
) -> None:
    inference_id = setup_create_feedback_tests
    status_code, feedback_response = client.post_feedback(
        target,
        score,
        reason,
        user_id,
        inference_id,
    )
    override_get_db_session()
    assert status_code == expected_response_code
    if 200 <= status_code <= 299:
        assert feedback_response is not None
        assert feedback_response.get("target", None) == target.value
        assert feedback_response.get("score", None) == score
        assert feedback_response.get("reason", None) == reason
        assert feedback_response.get("user_id", None) == user_id
