"""Runs of a saved prompt in the Arthur system task are recorded there as LLM spans."""

import json
import random
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import litellm
import pytest
from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from fastapi import HTTPException
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient, LLMModelResponse
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from repositories.agentic_prompts_repository import (
    AgenticPromptRepository,
    session_trace_id,
)
from repositories.system_task_repository import SystemTaskRepository
from schemas.request_schemas import CreateAgenticPromptRequest, PromptCompletionRequest
from schemas.response_schemas import AgenticPromptRunResponse
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from utils.constants import ARTHUR_SYSTEM_TASK_ID, DEFAULT_ORG_ID

GET_CLIENT = (
    "repositories.agentic_prompts_repository.ModelProviderRepository"
    ".get_model_provider_client"
)
ENQUEUE_EVALS = (
    "repositories.continuous_evals_repository.ContinuousEvalsRepository"
    ".enqueue_continuous_evals_for_root_spans"
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = override_get_db_session()
    SystemTaskRepository(session).initialize_system_tasks()
    yield session
    session.close()


@pytest.fixture
def prompt_name(db_session: Session) -> Generator[str, None, None]:
    """A system-task prompt of the test's own; it and its spans are deleted afterwards."""
    name = f"test_spans_{uuid4().hex}"
    AgenticPromptRepository(db_session).save_llm_item(
        ARTHUR_SYSTEM_TASK_ID,
        name,
        CreateAgenticPromptRequest(
            model_name="gpt-4o",
            model_provider=ModelProvider.OPENAI,
            messages=[
                OpenAIMessage(
                    role=MessageRole.USER, content="PROMPT-TEXT-MARKER {{ x }}"
                )
            ],
        ),
    )
    yield name
    spans = db_session.query(DatabaseSpan).filter(DatabaseSpan.span_name == name).all()
    trace_ids = {s.trace_id for s in spans}
    for span in spans:
        db_session.delete(span)
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id.in_(trace_ids),
    ).delete(synchronize_session=False)
    db_session.commit()
    AgenticPromptRepository(db_session).delete_llm_item(ARTHUR_SYSTEM_TASK_ID, name)


def _client(error: Exception | None = None) -> LLMClient:
    client = LLMClient(provider=ModelProvider.OPENAI, api_key="key")
    response = litellm.ModelResponse(
        choices=[{"message": {"role": "assistant", "content": "the reply"}}],
        usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    )
    client.completion = MagicMock(  # type: ignore[method-assign]
        side_effect=error,
        return_value=LLMModelResponse(response=response, cost="0.0125"),
    )
    return client


async def _run(
    session: Session,
    name: str,
    session_id: str | None = None,
    task_id: str = ARTHUR_SYSTEM_TASK_ID,
    error: Exception | None = None,
) -> Any:
    with patch(GET_CLIENT, return_value=_client(error)):
        return await AgenticPromptRepository(session).run_saved_prompt(
            task_id,
            name,
            "latest",
            PromptCompletionRequest(
                variables=[{"name": "x", "value": "VARIABLE-MARKER"}]
            ),
            org_id=DEFAULT_ORG_ID,
            session_id=session_id,
        )


def _spans(session: Session, name: str) -> list[DatabaseSpan]:
    return (
        session.query(DatabaseSpan)
        .filter(
            DatabaseSpan.task_id == ARTHUR_SYSTEM_TASK_ID,
            DatabaseSpan.span_name == name,
        )
        .all()
    )


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_run_is_recorded_as_an_llm_span_without_its_text(
    db_session: Session,
    prompt_name: str,
) -> None:
    with patch(ENQUEUE_EVALS) as enqueue:
        response = await _run(db_session, prompt_name)

    assert response.content == "the reply"
    [span] = _spans(db_session, prompt_name)
    assert span.span_kind == "LLM"
    assert span.parent_span_id is None
    assert span.status_code == "Ok"
    assert span.end_time >= span.start_time
    assert (span.prompt_token_count, span.completion_token_count) == (100, 20)
    assert span.total_token_count == 120
    attributes = json.dumps(span.raw_data)
    assert "gpt-4o" in attributes
    assert "0.0125" in attributes
    assert span.raw_data["attributes"]["metadata"] == {
        "prompt_name": prompt_name,
        "prompt_version": 1,
    }
    # Neither what was sent nor what came back.
    assert "PROMPT-TEXT-MARKER" not in attributes
    assert "VARIABLE-MARKER" not in attributes
    assert "the reply" not in attributes
    # Arthur's own calls never run continuous evals.
    enqueue.assert_not_called()


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_runs_with_one_session_id_share_a_session_and_a_trace(
    db_session: Session,
    prompt_name: str,
) -> None:
    await _run(db_session, prompt_name, session_id="onboarding_analysis:job-1")
    await _run(db_session, prompt_name, session_id="onboarding_analysis:job-1")

    spans = _spans(db_session, prompt_name)
    assert len(spans) == 2
    assert {s.session_id for s in spans} == {"onboarding_analysis:job-1"}
    assert {s.trace_id for s in spans} == {
        session_trace_id("onboarding_analysis:job-1").hex(),
    }


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_failed_run_is_recorded_with_its_error_type(
    db_session: Session,
    prompt_name: str,
) -> None:
    error = HTTPException(status_code=413, detail="quotes the user's text")

    with pytest.raises(HTTPException):
        await _run(db_session, prompt_name, error=error)

    [span] = _spans(db_session, prompt_name)
    assert span.status_code == "Error"
    assert "HTTPException 413" in json.dumps(span.raw_data)
    assert "user's text" not in json.dumps(span.raw_data)


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_run_in_another_task_records_nothing(db_session: Session) -> None:
    task_id = str(uuid4())
    name = f"test_spans_{uuid4().hex}"
    repo = AgenticPromptRepository(db_session)
    repo.save_llm_item(
        task_id,
        name,
        CreateAgenticPromptRequest(
            model_name="gpt-4o",
            model_provider=ModelProvider.OPENAI,
            messages=[OpenAIMessage(role=MessageRole.USER, content="hi {{ x }}")],
        ),
    )
    try:
        await _run(db_session, name, task_id=task_id)
        assert (
            db_session.query(DatabaseSpan).filter(DatabaseSpan.span_name == name).all()
            == []
        )
    finally:
        repo.delete_llm_item(task_id, name)


@pytest.mark.unit_tests
def test_the_route_passes_the_session_header_on(
    client: GenaiEngineTestClientBase,
) -> None:
    status_code, task = client.create_task(
        f"agentic_task_{random.random()}",
        is_agentic=True,
    )
    assert status_code == 200
    run = AsyncMock(return_value=AgenticPromptRunResponse(content="ok", cost="0"))

    with patch(
        "routers.v1.agentic_prompt_routes.AgenticPromptRepository.run_saved_prompt",
        run,
    ):
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/prompts/any/versions/production/completions",
            headers={
                **client.authorized_user_api_key_headers,
                "X-Arthur-Session-Id": "onboarding_analysis:job-1",
            },
        )

    assert response.status_code == 200
    assert run.call_args.kwargs["session_id"] == "onboarding_analysis:job-1"
