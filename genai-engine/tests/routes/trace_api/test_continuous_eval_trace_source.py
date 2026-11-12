"""A trace-scope continuous eval whose transform variable is the whole trace
(source='trace'): the judge reads every span, and the run row keeps a capped copy."""

import json
from unittest.mock import patch

import pytest

from repositories.continuous_evals_repository import ContinuousEvalsRepository
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.test_continuous_eval_execution import (
    mock_get_db_session_generator,
)
from tests.routes.trace_api.test_continuous_eval_span_scope import (
    WORKER,
    SyncQueue,
    _cleanup,
    _judge_reply,
    _runs,
    _setup_eval,
)
from tests.unit.routes.transforms.test_transform_span_order import (
    RETRY_TRACE,
    add_trace,
)
from utils.stored_value import STORED_VALUE_MAX_CHARS

WHOLE_TRACE = {"variable_name": "tool_output", "source": "trace", "attribute_path": ""}


def _judge_prompt(mock_completion) -> str:
    return json.dumps(mock_completion.call_args.kwargs.get("messages", ""))


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_judge_reads_every_span_of_the_trace(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """The retry trace: the first lookup_order times out, the second succeeds. A
    first-match variable would show the judge one call; the whole-trace value shows
    both, in tree order, in one judge call."""
    queue = SyncQueue()
    task, eval_id = _setup_eval(
        client,
        None,
        transform_variable=WHOLE_TRACE,
        scope="trace",
        span_filter=None,
    )
    trace_id = add_trace(task.id, RETRY_TRACE)
    try:
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        assert queue.drain() == 1
        assert mock_completion.call_count == 1
        prompt = _judge_prompt(mock_completion)
        assert "TRACE v1 spans=3" in prompt
        assert "[2] TOOL lookup_order" in prompt and "[3] TOOL lookup_order" in prompt
        assert "upstream timeout" in prompt and "delivered" in prompt

        (run,) = _runs(eval_id, trace_id)["trace"]
        # the mocked judge fails any prompt that shows the timeout
        assert run.run_status == "failed", run.annotation_description
        assert run.label == "tool_error"
        assert run.judged_span_count == 3
        (stored,) = run.input_variables
        assert stored["name"] == "tool_output"
        assert stored["value"].startswith("TRACE v1 spans=3 agent=1 tool=2")
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_judge_sees_the_full_text_and_the_run_keeps_a_capped_copy(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    queue = SyncQueue()
    task, eval_id = _setup_eval(
        client,
        None,
        transform_variable=WHOLE_TRACE,
        scope="trace",
        span_filter=None,
    )
    long_trace = [
        {"span_id": "root", "span_name": "agent", "span_kind": "AGENT", "offset_s": 0},
    ] + [
        {
            "span_id": f"read-{i}",
            "parent_span_id": "root",
            "span_name": "read_file",
            "offset_s": 1 + i,
            "output": f"file {i}: " + "x" * 1500,
        }
        for i in range(12)
    ]
    trace_id = add_trace(task.id, long_trace)
    try:
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        assert queue.drain() == 1
        prompt = _judge_prompt(mock_completion)
        assert "[13] TOOL read_file" in prompt  # the judge got every span

        (run,) = _runs(eval_id, trace_id)["trace"]
        assert run.run_status == "passed", run.annotation_description
        (stored,) = run.input_variables
        assert len(stored["value"]) <= STORED_VALUE_MAX_CHARS
        assert "sha256=" in stored["value"]  # the cut copy proves which text was judged
    finally:
        _cleanup(client, task, eval_id, queue)
