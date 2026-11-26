"""Runs of a saved prompt in the Arthur system task are recorded there as LLM spans."""

import json
import random
from datetime import datetime, timedelta, timezone
import threading
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
    session_root_span_id,
    session_trace_id,
)
from repositories.system_task_repository import SystemTaskRepository
from schemas.request_schemas import (
    CreateAgenticPromptRequest,
    PromptCompletionRequest,
    SystemTaskSessionSummary,
)
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
    trace_ids = {
        s.trace_id
        for s in db_session.query(DatabaseSpan).filter(DatabaseSpan.span_name == name)
    }
    spans = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.trace_id.in_(trace_ids))
        .all()
    )
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
async def test_a_run_is_recorded_as_an_llm_span_with_its_messages_and_reply(
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
    # What was sent (a short variable filled in) and what came back.
    assert span.raw_data["attributes"]["input"]["value"] == {
        "messages": [{"role": "user", "content": "PROMPT-TEXT-MARKER VARIABLE-MARKER"}],
    }
    assert span.raw_data["attributes"]["output"]["value"] == {"text": "the reply"}
    # Arthur's own calls never run continuous evals.
    enqueue.assert_not_called()


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_traces_passed_as_a_variable_are_recorded_as_a_pointer(
    db_session: Session,
    prompt_name: str,
) -> None:
    """The traces a feature sends are already stored in this engine: the span names
    them instead of copying them."""
    ids = [uuid4().hex, uuid4().hex]
    traces = "".join(f"<trace id={i}>{'TRACE-TEXT-MARKER ' * 200}</trace>" for i in ids)

    with patch(GET_CLIENT, return_value=_client()):
        await AgenticPromptRepository(db_session).run_saved_prompt(
            ARTHUR_SYSTEM_TASK_ID,
            prompt_name,
            "latest",
            PromptCompletionRequest(variables=[{"name": "x", "value": traces}]),
            org_id=DEFAULT_ORG_ID,
        )

    [span] = _spans(db_session, prompt_name)
    recorded = json.dumps(span.raw_data["attributes"]["input"]["value"])
    assert "TRACE-TEXT-MARKER" not in recorded
    assert f"2 traces stored in this engine, {len(traces):,} characters" in recorded
    assert all(i in recorded for i in ids)
    assert "PROMPT-TEXT-MARKER" in recorded


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
async def test_a_sessions_runs_sit_under_one_root_span_that_ends_with_the_last(
    db_session: Session,
    prompt_name: str,
) -> None:
    session_id = f"onboarding_analysis:{uuid4()}"
    await _run(db_session, prompt_name, session_id=session_id)
    await _run(db_session, prompt_name, session_id=session_id)

    runs = _spans(db_session, prompt_name)
    [root] = (
        db_session.query(DatabaseSpan)
        .filter(
            DatabaseSpan.trace_id == session_trace_id(session_id).hex(),
            DatabaseSpan.parent_span_id.is_(None),
        )
        .all()
    )
    assert root.span_id == session_root_span_id(session_id).hex()
    assert (root.span_name, root.span_kind) == ("onboarding_analysis", "AGENT")
    assert root.session_id == session_id
    assert {s.parent_span_id for s in runs} == {root.span_id}
    assert root.start_time <= min(s.start_time for s in runs)
    assert root.end_time == max(s.end_time for s in runs)
    assert root.raw_data["endTimeUnixNano"] == max(
        s.raw_data["endTimeUnixNano"] for s in runs
    )


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_the_model_call_runs_off_the_event_loop(
    db_session: Session,
    prompt_name: str,
) -> None:
    """A blocking call on the event loop would hold every other request, so a
    caller's parallel calls would be answered one after another."""
    loop_thread = threading.get_ident()
    client = _client()
    called_on: list[int] = []
    completion = client.completion
    client.completion = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda *a, **k: called_on.append(threading.get_ident())
        or completion.return_value,
    )

    with patch(GET_CLIENT, return_value=client):
        await AgenticPromptRepository(db_session).run_saved_prompt(
            ARTHUR_SYSTEM_TASK_ID,
            prompt_name,
            "latest",
            PromptCompletionRequest(variables=[{"name": "x", "value": "v"}]),
            org_id=DEFAULT_ORG_ID,
        )

    assert called_on and called_on[0] != loop_thread


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


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_session_summary_makes_the_root_cover_the_whole_job(
    db_session: Session,
    prompt_name: str,
) -> None:
    session_id = f"onboarding_analysis:{uuid4()}"
    await _run(db_session, prompt_name, session_id=session_id)
    [run] = _spans(db_session, prompt_name)
    job_start = datetime.now(timezone.utc) - timedelta(seconds=30)
    job_end = datetime.now(timezone.utc) + timedelta(seconds=1)
    summary = SystemTaskSessionSummary(
        started_at=job_start,
        ended_at=job_end,
        status="error",
        status_message="stopped at the cost cap",
        input={"agent_task_id": "task-1", "window_days": 30},
        output={"outcome": "completed", "traces_read": 134},
        steps=[
            {
                "name": "read_traces",
                "started_at": job_start,
                "ended_at": job_start + timedelta(seconds=10),
                "attributes": {"traces": 134},
            },
        ],
    )
    repo = AgenticPromptRepository(db_session)
    repo.record_session_summary(session_id, summary)
    repo.record_session_summary(session_id, summary)  # a retry adds nothing

    in_trace = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.trace_id == session_trace_id(session_id).hex())
        .all()
    )
    [root] = [s for s in in_trace if s.parent_span_id is None]
    [step] = [s for s in in_trace if s.span_name == "read_traces"]
    assert root.span_id == session_root_span_id(session_id).hex()
    assert (root.span_name, root.span_kind, root.status_code) == (
        "onboarding_analysis",
        "AGENT",
        "Error",
    )
    assert root.start_time <= step.start_time < run.start_time
    assert root.end_time >= run.end_time
    assert root.raw_data["attributes"]["input"]["value"] == summary.input
    assert root.raw_data["attributes"]["output"]["value"] == summary.output
    assert (step.span_kind, step.parent_span_id) == ("CHAIN", root.span_id)
    assert run.parent_span_id == root.span_id
