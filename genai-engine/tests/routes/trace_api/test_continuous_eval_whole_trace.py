"""A continuous eval whose transform variable is the whole trace: one judge call
sees every attempt of a retried tool call, so it can say the run eventually
succeeded."""

import json
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from litellm.types.utils import ModelResponse

from services.continuous_eval import (
    ContinuousEvalJob,
    get_continuous_eval_queue_service,
    initialize_continuous_eval_queue_service,
    shutdown_continuous_eval_queue_service,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.routes.trace_api.test_continuous_eval_execution import (
    cleanup_model_provider,
    create_mock_annotation,
    delete_mock_annotation,
    mock_get_db_session_generator,
)
from tests.unit.routes.transforms.test_transform_whole_trace import (
    WHOLE_TRACE,
    add_trace,
    delete_traces,
)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_one_judge_call_sees_every_attempt_of_a_retry(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "search failed twice, then found flights.", "score": 1}',
    }
    mock_completion.return_value = mock_response

    initialize_continuous_eval_queue_service(num_workers=1, override_execution_delay=0)
    queue_service = get_continuous_eval_queue_service()
    status_code, task = client.create_task(name="whole_trace_eval", is_agentic=True)
    assert status_code == 200
    annotation = None
    try:
        response = client.base_client.put(
            "/api/v1/model_providers/openai",
            json={"api_key": "test-key"},
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 201
        status_code, _ = client.save_llm_eval(
            task_id=task.id,
            llm_eval_name="eventual_success",
            llm_eval_data={
                "model_name": "gpt-4o",
                "model_provider": "openai",
                "instructions": "Did the run eventually succeed?\n\n{{trace}}",
            },
        )
        assert status_code == 200
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="whole trace",
            definition={"variables": [WHOLE_TRACE]},
        )
        assert status_code == 200
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=task.id,
            continuous_eval_data={
                "name": "eventual success",
                "llm_eval_name": "eventual_success",
                "llm_eval_version": 1,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {"transform_variable": "trace", "eval_variable": "trace"},
                ],
            },
        )
        assert status_code == 200

        trace_id = add_trace(task.id)
        annotation = create_mock_annotation(
            trace_id=trace_id,
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            continuous_eval_id=continuous_eval.id,
            run_status=ContinuousEvalRunStatus.PENDING,
        )
        queue_service._execute_job(
            ContinuousEvalJob(
                annotation_id=annotation.id,
                trace_id=trace_id,
                continuous_eval_id=continuous_eval.id,
                task_id=task.id,
                delay_seconds=0,
            ),
        )

        assert mock_completion.call_count == 1
        prompt = json.dumps(mock_completion.call_args.kwargs.get("messages", ""))
        assert "TRACE v1 spans=4" in prompt
        for text in (
            "timeout after 30s",
            "HTTP 500 from flight API",
            "3 flights found",
        ):
            assert text in prompt

        status_code, run = client.get_annotation_by_id(annotation.id)
        assert status_code == 200
        assert run.run_status == ContinuousEvalRunStatus.PASSED.value
    finally:
        if annotation is not None:
            delete_mock_annotation(annotation.id)
        delete_traces(task.id)
        client.delete_task(task.id)
        shutdown_continuous_eval_queue_service()
        cleanup_model_provider(client)
