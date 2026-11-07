"""Annotations carry the span they are about and a category label, from people and judges."""

from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from litellm.types.utils import ModelResponse

from schemas.llm_eval_schemas import ReasonedScore
from services.continuous_eval import (
    ContinuousEvalJob,
    get_continuous_eval_queue_service,
    initialize_continuous_eval_queue_service,
    shutdown_continuous_eval_queue_service,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.routes.trace_api.test_continuous_eval_execution import (
    cleanup_model_provider,
    cleanup_test_data,
    create_mock_annotation,
    delete_mock_annotation,
    mock_get_db_session_generator,
    setup_test_data,
)


def _annotate(client, trace_id, body):
    return client.base_client.post(
        f"/api/v1/traces/{trace_id}/annotations",
        json=body,
        headers=client.authorized_user_api_key_headers,
    )


@pytest.mark.unit_tests
def test_human_annotation_keeps_span_id_and_label(client: GenaiEngineTestClientBase):
    test_data = setup_test_data()
    trace_id = test_data["trace_id"]
    span_a, span_b = test_data["spans"][0].span_id, test_data["spans"][1].span_id
    try:
        resp = _annotate(
            client,
            trace_id,
            {
                "annotation_score": 0,
                "annotation_description": "called the wrong tool",
                "span_id": span_a,
                "label": "wrong_tool",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["span_id"] == span_a
        assert resp.json()["label"] == "wrong_tool"

        # Another span and the whole trace each keep their own annotation.
        assert (
            _annotate(
                client,
                trace_id,
                {"annotation_score": 1, "span_id": span_b, "label": "ok"},
            ).status_code
            == 200
        )
        assert (
            _annotate(
                client,
                trace_id,
                {"annotation_score": 0, "annotation_description": "bad turn"},
            ).status_code
            == 200
        )

        listed = client.base_client.get(
            f"/api/v1/traces/{trace_id}/annotations",
            headers=client.authorized_user_api_key_headers,
        ).json()["annotations"]
        human = {
            (a.get("span_id"), a.get("label"), a["annotation_score"])
            for a in listed
            if a["annotation_type"] == "human"
        }
        assert human == {(span_a, "wrong_tool", 0), (span_b, "ok", 1), (None, None, 0)}

        # Re-annotating a span updates that span's annotation only.
        assert (
            _annotate(
                client,
                trace_id,
                {"annotation_score": 0, "span_id": span_a, "label": "wrong_args"},
            ).status_code
            == 200
        )
        listed = client.base_client.get(
            f"/api/v1/traces/{trace_id}/annotations",
            headers=client.authorized_user_api_key_headers,
        ).json()["annotations"]
        labels = sorted(
            a.get("label") or "" for a in listed if a["annotation_type"] == "human"
        )
        assert labels == ["", "ok", "wrong_args"]

        resp = _annotate(
            client, trace_id, {"annotation_score": 0, "span_id": "not-in-this-trace"}
        )
        assert resp.status_code == 400
        assert "not in trace" in resp.json()["detail"]
    finally:
        client.base_client.delete(
            f"/api/v1/traces/{trace_id}/annotations",
            headers=client.authorized_user_api_key_headers,
        )
        cleanup_test_data(test_data)


@pytest.mark.unit_tests
def test_judge_schema_asks_for_a_label_but_old_replies_still_parse():
    assert ReasonedScore.model_json_schema()["required"] == ["reason", "score", "label"]
    assert (
        ReasonedScore.model_validate_json('{"reason": "r", "score": 1}').label is None
    )


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_judge_label_is_stored_on_the_run(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    test_data = setup_test_data()
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "cancel_order for a refund request", "score": 0, "label": "wrong_tool"}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001
    initialize_continuous_eval_queue_service(num_workers=1, override_execution_delay=0)
    status_code, task = client.create_task(name="test_judge_label", is_agentic=True)
    assert status_code == 200
    annotation = None
    try:
        assert (
            client.base_client.put(
                "/api/v1/model_providers/openai",
                json={"api_key": "test-key"},
                headers=client.authorized_user_api_key_headers,
            ).status_code
            == 201
        )
        status_code, _ = client.save_llm_eval(
            task_id=task.id,
            llm_eval_name="labelled_eval",
            llm_eval_data={
                "model_name": "gpt-4o",
                "model_provider": "openai",
                "instructions": "Label the tool call [ok|wrong_tool]: {{model_name}}",
            },
        )
        assert status_code == 200
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="labelled_transform",
            description="",
            definition={
                "variables": [
                    {
                        "variable_name": "model_name",
                        "span_name": "rag-retrieval-savedQueries",
                        "attribute_path": "attributes.input.value.context",
                    },
                ],
            },
        )
        assert status_code == 200
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=task.id,
            continuous_eval_data={
                "name": "labelled_continuous_eval",
                "llm_eval_name": "labelled_eval",
                "llm_eval_version": 1,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {"transform_variable": "model_name", "eval_variable": "model_name"},
                ],
            },
        )
        assert status_code == 200
        annotation = create_mock_annotation(
            trace_id=test_data["trace_id"],
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            continuous_eval_id=continuous_eval.id,
            run_status=ContinuousEvalRunStatus.PENDING,
        )
        get_continuous_eval_queue_service()._execute_job(
            ContinuousEvalJob(
                annotation_id=annotation.id,
                trace_id=test_data["trace_id"],
                continuous_eval_id=continuous_eval.id,
                task_id=task.id,
                delay_seconds=0,
            ),
        )
        run = client.base_client.get(
            f"/api/v1/traces/annotations/{annotation.id}",
            headers=client.authorized_user_api_key_headers,
        ).json()
        assert run["run_status"] == ContinuousEvalRunStatus.FAILED.value
        assert run["label"] == "wrong_tool"
        results = client.base_client.get(
            f"/api/v1/tasks/{task.id}/continuous_evals/results",
            headers=client.authorized_user_api_key_headers,
        ).json()["annotations"]
        assert [r.get("label") for r in results] == ["wrong_tool"]
    finally:
        if annotation is not None:
            delete_mock_annotation(annotation.id)
        client.delete_task(task.id)
        shutdown_continuous_eval_queue_service()
        cleanup_model_provider(client)
        cleanup_test_data(test_data)
