import uuid
from datetime import datetime

import pytest
from db_models.db_models import (
    DatabaseInference,
    DatabaseInferenceFeedback,
    DatabaseInferencePrompt,
    DatabaseInferencePromptContent,
    DatabaseInferenceResponse,
    DatabaseInferenceResponseContent,
)
from schemas.enums import InferenceFeedbackTarget, PaginationSortMethod, RuleResultEnum
from sqlalchemy.orm import Session
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.unit.routes.feedback import FEEDBACK_DB_SESSION

NUM_INFERENCES_IN_FEEDBACK_TEST = 3


@pytest.fixture(scope="module", autouse=True)
def setup_query_feedback_tests():
    db_session = FEEDBACK_DB_SESSION
    initialize_inferences(db_session)
    initialize_feedback(db_session)
    yield
    cleanup_test_data(db_session)


def initialize_inferences(db_session: Session) -> None:
    db_session.begin()
    for i in range(NUM_INFERENCES_IN_FEEDBACK_TEST):
        db_prompt = DatabaseInferencePrompt(
            id=f"tqf_prompt_id_{i}",
            inference_id=f"tqf_inference_id_{i}",
            result=RuleResultEnum.PASS.value,
            content=DatabaseInferencePromptContent(
                inference_prompt_id=f"tqf_prompt_id_{i}",
                content=f"tqf_prompt_message_{i}",
            ),
            prompt_rule_results=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_response = DatabaseInferenceResponse(
            id=f"tqf_response_id_{i}",
            inference_id=f"tqf_inference_id_{i}",
            result=RuleResultEnum.PASS.value,
            content=DatabaseInferenceResponseContent(
                inference_response_id=f"tqf_response_id_{i}",
                content=f"tqf_response_message_{i}",
            ),
            response_rule_results=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        inference_user_id = f"tqf_user_id_{i}"
        if i == 1:
            inference_user_id = "tqf_special_user_id_11"
        elif i == 2:
            inference_user_id = "tqf_special_user_id_212"
        db_inference = DatabaseInference(
            id=f"tqf_inference_id_{i}",
            result=RuleResultEnum.PASS.value,
            inference_prompt=db_prompt,
            inference_response=db_response,
            conversation_id=f"tqf_conversation_id_{i}",
            task_id=f"tqf_task_id_{i}",
            user_id=inference_user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(db_inference)
    db_session.commit()


def initialize_feedback(db_session: Session) -> None:
    feedback_data = [
        (InferenceFeedbackTarget.CONTEXT, 0, "r1", "tqf_inference_id_0", "u0"),
        (InferenceFeedbackTarget.CONTEXT, 1, "r2", "tqf_inference_id_0", "u11"),
        (InferenceFeedbackTarget.PROMPT_RESULTS, 0, "r3", "tqf_inference_id_0", "u0"),
        (InferenceFeedbackTarget.RESPONSE_RESULTS, 0, "r4", "tqf_inference_id_0", None),
        (InferenceFeedbackTarget.PROMPT_RESULTS, 1, "r5", "tqf_inference_id_1", "u0"),
        (InferenceFeedbackTarget.PROMPT_RESULTS, 1, "r6", "tqf_inference_id_1", "u11"),
        (InferenceFeedbackTarget.PROMPT_RESULTS, 0, "r7", "tqf_inference_id_1", "u0"),
        (InferenceFeedbackTarget.RESPONSE_RESULTS, 0, "r8", "tqf_inference_id_1", "u0"),
        (InferenceFeedbackTarget.RESPONSE_RESULTS, 0, "r9", "tqf_inference_id_1", "u0"),
        (InferenceFeedbackTarget.CONTEXT, -1, "r10", "tqf_inference_id_2", "u11"),
        (InferenceFeedbackTarget.CONTEXT, 0, "r11", "tqf_inference_id_2", "u0"),
        (InferenceFeedbackTarget.CONTEXT, 1, "r12", "tqf_inference_id_2", "u212"),
    ]

    db_session.begin()
    db_session.query(DatabaseInferenceFeedback).delete()  # Ensure clean table
    for i, (target, score, reason, inference_id, user_id) in enumerate(feedback_data):
        db_feedback = DatabaseInferenceFeedback(
            id=f"tqf_feedback_id_{i}",
            inference_id=inference_id,
            target=target,
            score=score,
            reason=reason,
            user_id=user_id,
        )
        db_session.add(db_feedback)
    db_session.commit()


def cleanup_test_data(db_session: Session) -> None:
    db_session.begin()
    db_session.query(DatabaseInferenceFeedback).where(
        DatabaseInferenceFeedback.inference_id.in_(
            ["tqf_inference_id_0", "tqf_inference_id_1", "tqf_inference_id_2"],
        ),
    ).delete()  # cleanup feedback
    db_session.query(DatabaseInferenceResponse).where(
        DatabaseInferenceResponse.inference_id.in_(
            ["tqf_inference_id_0", "tqf_inference_id_1", "tqf_inference_id_2"],
        ),
    ).delete()  # cleanup response
    db_session.query(DatabaseInferencePrompt).where(
        DatabaseInferencePrompt.inference_id.in_(
            ["tqf_inference_id_0", "tqf_inference_id_1", "tqf_inference_id_2"],
        ),
    ).delete()  # cleanup prompt
    db_session.query(DatabaseInference).where(
        DatabaseInference.id.in_(
            ["tqf_inference_id_0", "tqf_inference_id_1", "tqf_inference_id_2"],
        ),
    ).delete()  # cleanup inference
    db_session.commit()


@pytest.mark.parametrize(
    "query_params,expectations",
    [
        pytest.param(
            {},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 10,
                "total_feedback_items_found": 12,
            },
            id="no filters, no pagination settings",
        ),
        pytest.param(
            {"page_size": 20},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 12,
                "total_feedback_items_found": 12,
            },
            id="no filters, high pagination settings",
        ),
        pytest.param(
            {"page": 1, "page_size": 5},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 5,
                "total_feedback_items_found": 12,
            },
            id="no filters, specific pagination settings",
        ),
        pytest.param(
            {"page": 2, "page_size": 5},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 2,
                "total_feedback_items_found": 12,
            },
            id="no filters, specific pagination settings, last page",
        ),
        pytest.param(
            {
                "sort": PaginationSortMethod.DESCENDING,
                "page": 0,
                "page_size": 20,
                "start_time": datetime(1900, 1, 1),
                "end_time": datetime(3000, 12, 31),
                "feedback_id": [
                    "tqf_feedback_id_0",
                    "tqf_feedback_id_1",
                    "tqf_feedback_id_2",
                    "tqf_feedback_id_3",
                    "tqf_feedback_id_4",
                    "tqf_feedback_id_5",
                    "tqf_feedback_id_6",
                    "tqf_feedback_id_7",
                    "tqf_feedback_id_8",
                    "tqf_feedback_id_9",
                    "tqf_feedback_id_10",
                    "tqf_feedback_id_11",
                ],
                "inference_id": [
                    "tqf_inference_id_0",
                    "tqf_inference_id_1",
                    "tqf_inference_id_2",
                ],
                "target": [
                    str(InferenceFeedbackTarget.CONTEXT.value),
                    str(InferenceFeedbackTarget.PROMPT_RESULTS.value),
                    str(InferenceFeedbackTarget.RESPONSE_RESULTS.value),
                ],
                "score": [-1, 0, 1],
                "feedback_user_id": None,
                "conversation_id": [
                    "tqf_conversation_id_0",
                    "tqf_conversation_id_1",
                    "tqf_conversation_id_2",
                ],
                "task_id": [
                    "tqf_task_id_0",
                    "tqf_task_id_1",
                    "tqf_task_id_2",
                ],
                "inference_user_id": "%u%",
            },
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 12,
                "total_feedback_items_found": 12,
            },
            id="filters, everything found",
        ),
        pytest.param(
            {"start_time": datetime(3000, 12, 31)},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="start time filter high, 0 results",
        ),
        pytest.param(
            {"start_time": datetime(1900, 1, 1)},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 10,
                "total_feedback_items_found": 12,
            },
            id="start time filter low, all results",
        ),
        pytest.param(
            {"end_time": datetime(1900, 1, 1)},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="end time filter low, 0 results",
        ),
        pytest.param(
            {"end_time": datetime(3000, 12, 31)},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 10,
                "total_feedback_items_found": 12,
            },
            id="end time filter high, all results",
        ),
        pytest.param(
            {"feedback_id": "tqf_feedback_id_0"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 1,
                "total_feedback_items_found": 1,
            },
            id="single feedback_ids",
        ),
        pytest.param(
            {
                "feedback_id": [
                    "tqf_feedback_id_1",
                    "tqf_feedback_id_2",
                ],
            },
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 2,
                "total_feedback_items_found": 2,
            },
            id="multiple feedback_ids",
        ),
        pytest.param(
            {"feedback_id": "non-existent-feedback-id"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="feedback_id which does not exist",
        ),
        pytest.param(
            {"inference_id": "tqf_inference_id_0"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 4,
                "total_feedback_items_found": 4,
            },
            id="single inference_id",
        ),
        pytest.param(
            {
                "inference_id": [
                    "tqf_inference_id_1",
                    "tqf_inference_id_2",
                ],
            },
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 8,
                "total_feedback_items_found": 8,
            },
            id="multiple inference_ids",
        ),
        pytest.param(
            {"inference_id": uuid.uuid4()},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="inference_id which does not exist",
        ),
        pytest.param(
            {"target": str(InferenceFeedbackTarget.CONTEXT.value)},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 5,
                "total_feedback_items_found": 5,
            },
            id="single target",
        ),
        pytest.param(
            {
                "target": [
                    str(InferenceFeedbackTarget.RESPONSE_RESULTS.value),
                    str(InferenceFeedbackTarget.PROMPT_RESULTS.value),
                ],
            },
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 7,
                "total_feedback_items_found": 7,
            },
            id="multiple targets",
        ),
        pytest.param(
            {"target": "nonsense"},
            {
                "expected_response_code": 400,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="invalid target",
        ),
        pytest.param(
            {"score": 1},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 4,
                "total_feedback_items_found": 4,
            },
            id="single score",
        ),
        pytest.param(
            {"score": [0, -1]},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 8,
                "total_feedback_items_found": 8,
            },
            id="multiple scores",
        ),
        pytest.param(
            {"score": 2},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="score which is not in dataset",
        ),
        pytest.param(
            {"feedback_user_id": "u0"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 7,
                "total_feedback_items_found": 7,
            },
            id="feedback_user_id 'u0' filter",
        ),
        pytest.param(
            {"feedback_user_id": "%1%"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 4,
                "total_feedback_items_found": 4,
            },
            id="feedback_user_id fuzzy search '%1%' filter",
        ),
        pytest.param(
            {"feedback_user_id": "non_user_id"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="invalid feedback_user_id",
        ),
        pytest.param(
            {"conversation_id": "tqf_conversation_id_0"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 4,
                "total_feedback_items_found": 4,
            },
            id="single conversation_id",
        ),
        pytest.param(
            {
                "conversation_id": [
                    "tqf_conversation_id_1",
                    "tqf_conversation_id_2",
                ],
            },
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 8,
                "total_feedback_items_found": 8,
            },
            id="multiple conversation_ids",
        ),
        pytest.param(
            {"conversation_id": "non_conversation_id"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="invalid conversation_id",
        ),
        pytest.param(
            {"task_id": "tqf_task_id_0"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 4,
                "total_feedback_items_found": 4,
            },
            id="single task_id",
        ),
        pytest.param(
            {
                "task_id": [
                    "tqf_task_id_1",
                    "tqf_task_id_2",
                ],
            },
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 8,
                "total_feedback_items_found": 8,
            },
            id="multiple task_ids",
        ),
        pytest.param(
            {"task_id": "non_task_id"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="invalid task_id",
        ),
        pytest.param(
            {"inference_user_id": "tqf_user_id_0"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 4,
                "total_feedback_items_found": 4,
            },
            id="single 'tqf_user_id_0' inference_user_id filter",
        ),
        pytest.param(
            {"inference_user_id": "%special%"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 8,
                "total_feedback_items_found": 8,
            },
            id="inference_user_id fuzzy search '%special%' filter",
        ),
        pytest.param(
            {"inference_user_id": "non_user_id"},
            {
                "expected_response_code": 200,
                "feedback_items_displayed": 0,
                "total_feedback_items_found": 0,
            },
            id="invalid inference_user_id",
        ),
    ],
)
@pytest.mark.unit_tests
def test_query_feedback(
    query_params: dict[str, any],
    expectations: dict[str, any],
    client: GenaiEngineTestClientBase,
) -> None:
    expected_response_code = expectations.get("expected_response_code", None)
    feedback_items_displayed = expectations.get("feedback_items_displayed", None)
    total_feedback_items_found = expectations.get("total_feedback_items_found", None)

    status_code, query_resp = client.query_feedback(**query_params)
    assert status_code == expected_response_code
    if 200 <= status_code <= 299:
        assert len(query_resp.feedback) == feedback_items_displayed
        assert query_resp.total_count == total_feedback_items_found


@pytest.mark.unit_tests
def test_query_feedback_response_model(client: GenaiEngineTestClientBase) -> None:
    status_code, query_resp = client.query_feedback(feedback_id="tqf_feedback_id_0")
    assert status_code == 200
    assert query_resp.total_count is not None
    assert query_resp.total_count == 1
    assert query_resp.page is not None
    assert query_resp.page == 0
    assert query_resp.page_size is not None
    assert query_resp.page_size == 10
    assert query_resp.total_pages is not None
    assert query_resp.total_pages == 1
    assert query_resp.feedback is not None
    assert len(query_resp.feedback) == 1
    for feedback in query_resp.feedback:
        assert feedback.id is not None
        assert feedback.id == "tqf_feedback_id_0"
        assert feedback.inference_id is not None
        assert feedback.inference_id == "tqf_inference_id_0"
        assert feedback.target is not None
        assert feedback.target == InferenceFeedbackTarget.CONTEXT.value
        assert feedback.score is not None
        assert feedback.score == 0
        assert feedback.reason is not None
        assert feedback.reason == "r1"
        assert feedback.user_id is not None
        assert feedback.user_id == "u0"
        assert feedback.created_at is not None
        assert feedback.created_at.year == datetime.now().year
        assert feedback.updated_at is not None
        assert feedback.updated_at.year == datetime.now().year
