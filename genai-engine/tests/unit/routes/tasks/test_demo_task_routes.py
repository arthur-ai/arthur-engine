import os
import uuid
from unittest.mock import patch

import pytest
from arthur_common.models.llm_model_providers import MessageRole, OpenAIMessage
from fastapi import HTTPException

from services.chatbot.demo_chatbot_service import DEMO_CONVERSATION_HISTORIES
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
)


async def stream_patch(*args, **kwargs):
    yield 'event: final_response\ndata: {"content": "hello from the demo chatbot"}\n\n'


@pytest.mark.unit_tests
def test_create_demo_task_returns_400_when_demo_mode_disabled(
    client: GenaiEngineTestClientBase,
):
    """Demo task creation is rejected when demo mode is not enabled."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GENAI_ENGINE_DEMO_MODE", None)
        status_code, task = client.create_demo_task()

    assert status_code == 400
    assert task is None


@pytest.mark.unit_tests
def test_create_demo_task_succeeds_when_demo_mode_enabled(
    client: GenaiEngineTestClientBase,
):
    """Test the demo task is created with all demo items when demo mode is enabled.

    Verifies the route creates the agentic prompts, trace transforms,
    continuous evals, dataset, and replayed traces, and that the
    continuous-eval enqueue step receives the replayed spans but does not
    actually enqueue any background jobs.
    """
    # Add anthropic model provider
    response = client.base_client.put(
        f"/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    try:
        with (
            patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
            patch(
                "repositories.continuous_evals_repository.ContinuousEvalsRepository.enqueue_continuous_evals_for_root_spans",
                return_value=None,
            ) as mock_enqueue,
        ):
            status_code, task = client.create_demo_task()

            assert status_code == 200
            assert task is not None
            assert task.name == "Demo Task"
            assert task.is_agentic is True

            status_code, fetched_task = client.get_task(task.id)
            assert status_code == 200
            assert fetched_task.id == task.id

            # Replayed traces are handed to the enqueue method, but no jobs are
            # actually enqueued (the real implementation is patched out).
            mock_enqueue.assert_called_once()
            enqueued_spans = mock_enqueue.call_args.args[0]
            assert len(enqueued_spans) > 0

            # Demo items exist on the task: 2 agentic prompts, 2 trace transforms,
            # 3 continuous evals, 1 dataset, and 3 replayed traces.
            status_code, _ = client.get_agentic_prompt(task.id, "demo_task_prompt", "1")
            assert status_code == 200
            status_code, _ = client.get_agentic_prompt(
                task.id,
                "demo_chatbot_summarizer_prompt",
                "1",
            )
            assert status_code == 200

            status_code, transforms = client.list_transforms(task.id)
            assert status_code == 200
            transform_names = {t.name for t in transforms.transforms}
            assert transform_names == {
                "Answer Relevance Eval",
                "Response Extraction Transform",
            }

            status_code, continuous_evals = client.list_continuous_evals(task.id)
            assert status_code == 200
            eval_names = {e.name for e in continuous_evals.evals}
            assert eval_names == {
                "Answer Relevance Continuous Eval",
                "Conciseness Continuous Eval",
                "Readability Continuous Eval",
            }

            status_code, datasets = client.search_datasets(task.id)
            assert status_code == 200
            assert len(datasets.datasets) == 1
            assert datasets.datasets[0].name == "Demo Dataset"

            status_code, traces = client.query_traces(task_ids=[task.id])
            assert status_code == 200
            assert traces.count == 3
    finally:
        # Cleanup
        response = client.base_client.delete(
            f"/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 204

        status_code = client.delete_task(task.id)
        assert status_code == 204


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "raised_exception,expected_status",
    [
        (ValueError("no model provider"), 400),
        (HTTPException(status_code=422, detail="bad demo data"), 422),
        (RuntimeError("kaboom"), 500),
    ],
    ids=["value_error", "http_exception", "unexpected_exception"],
)
def test_create_demo_task_archives_task_when_demo_items_raise(
    client: GenaiEngineTestClientBase,
    raised_exception: Exception,
    expected_status: int,
):
    """If demo item creation raises, route returns mapped status and archives the partial task."""
    captured_task_ids: list[str] = []

    def raise_on_create_items(self, task_id: str, user_id: str) -> None:
        captured_task_ids.append(task_id)
        raise raised_exception

    with (
        patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
        patch(
            "routers.v1.demo_task_routes.DemoTaskRepository.create_demo_items_for_task",
            new=raise_on_create_items,
        ),
    ):
        status_code, task = client.create_demo_task()

    assert status_code == expected_status
    assert task is None
    assert len(captured_task_ids) == 1

    # The partial task should be archived, so get_task returns 404
    status_code, _ = client.get_task(captured_task_ids[0])
    assert status_code == 404


@pytest.mark.unit_tests
def test_clear_chatbot_history_success(client: GenaiEngineTestClientBase):
    with (
        patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
        patch(
            "routers.v1.demo_task_routes.DemoTaskRepository.create_demo_items_for_task",
            return_value=None,
        ),
    ):
        status_code, task = client.create_demo_task()

    assert status_code == 200
    assert task is not None
    assert task.name == "Demo Task"
    assert task.is_agentic is True

    # Clearing history when it is empty should succeed
    status_code, _ = client.clear_demo_chatbot_history(task.id)
    assert status_code == 204

    _, keys = client.get_api_keys()
    user_id = next(k.id for k in keys if k.description == "TestClient")

    DEMO_CONVERSATION_HISTORIES[(task.id, user_id)] = [
        OpenAIMessage(role=MessageRole.USER, content="hello"),
    ]

    # Clearing history when it is not empty should succeed
    status_code, _ = client.clear_demo_chatbot_history(task.id)
    assert status_code == 204
    assert (task.id, user_id) not in DEMO_CONVERSATION_HISTORIES


@pytest.mark.unit_tests
def test_clear_chatbot_history_for_non_existent_task_fails(
    client: GenaiEngineTestClientBase,
):
    # Clearing history when it is empty should succeed
    status_code, response = client.clear_demo_chatbot_history(str(uuid.uuid4()))
    assert status_code == 404
    assert "not found" in response


@pytest.mark.unit_tests
def test_stream_demo_chatbot_streams_response(client: GenaiEngineTestClientBase):
    """Streaming the demo chatbot returns the SSE events yielded by stream."""
    # Set up Anthropic provider so the demo task can pick a model provider.
    response = client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    try:
        with (
            patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
            patch(
                "repositories.continuous_evals_repository.ContinuousEvalsRepository.enqueue_continuous_evals_for_root_spans",
                return_value=None,
            ),
            patch(
                "services.chatbot.base_chatbot_service.BaseChatbotService.stream",
                new=stream_patch,
            ),
        ):
            status_code, task = client.create_demo_task()
            assert status_code == 200

            status_code, body = client.stream_demo_chatbot(task.id, "hi")

            assert status_code == 200
            assert "final_response" in body
            assert "hello from the demo chatbot" in body
    finally:
        response = client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 204

        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_stream_demo_chatbot_yields_error_when_stream_raises(
    client: GenaiEngineTestClientBase,
):
    """If stream raises, safe_stream catches it and yields an SSE error event."""
    response = client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    try:
        with (
            patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
            patch(
                "repositories.continuous_evals_repository.ContinuousEvalsRepository.enqueue_continuous_evals_for_root_spans",
                return_value=None,
            ),
            patch(
                "services.chatbot.base_chatbot_service.BaseChatbotService.stream",
                side_effect=RuntimeError("stream failed"),
            ),
        ):
            status_code, task = client.create_demo_task()
            assert status_code == 200

            status_code, body = client.stream_demo_chatbot(task.id, "hi")

            assert status_code == 200
            assert "event: error" in body
            assert "Failed to stream chatbot response" in body
            assert "stream failed" in body
    finally:
        response = client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 204

        client.delete_task(task.id)
