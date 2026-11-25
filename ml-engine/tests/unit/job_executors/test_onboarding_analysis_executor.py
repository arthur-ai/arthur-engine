"""OnboardingAnalysisExecutor over fixture trace sets.

The connector is faked; everything after it is real: the metrics job's DatasetLoader
loads the rows into DuckDB under the agentic trace schema, and the executor's SQL runs
on them. Rows are shaped like the GenAI Engine's trace list, with trace-level aggregates
taken over every span, GUARDRAIL ones included, as the engine stores them.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import arthur_client.api_bindings as api_bindings
import duckdb
import pytest
from arthur_client.api_bindings import ApiClient, Configuration
from arthur_common.models.connectors import SHIELD_DATASET_TASK_ID_FIELD
from arthur_common.models.enums import ModelProblemType
from pydantic import ValidationError

from arthur_client_support import ONBOARDING_ANALYSIS_SUPPORTED
from config import Config
from connectors.connector import ConnectorReadResult
from dataset_loader import DatasetLoader
from job_executors import onboarding_analysis_executor
from job_executors.onboarding_analysis_executor import (
    INSIGHT_NOT_IMPLEMENTED,
    OnboardingAddress,
    OnboardingAnalysisExecutor,
    OnboardingAnalysisJobSpec,
    OnboardingAnalysisResult,
    OnboardingError,
    OnboardingErrorCode,
    OnboardingOutcome,
    OnboardingReport,
    OnboardingResultNotSent,
    PlatformOnboardingResultUploader,
    SampleSummary,
    _draw_sample,
    _finding,
)
from job_executors.onboarding_insights import MergedVerdict

NOW = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)
TASK_ID = str(uuid.uuid4())

logger = logging.getLogger("test-onboarding-analysis-executor")


def _span(
    trace_id: str,
    name: str,
    kind: str | None,
    start: datetime,
    seconds: float = 1.0,
    parent: str | None = None,
    status: str = "Ok",
    tokens: int | None = None,
    cost: float | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    if model:
        attributes["llm"] = {"model_name": model}
    return {
        "id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "span_id": uuid.uuid4().hex[:16],
        "parent_span_id": parent,
        "span_kind": kind,
        "span_name": name,
        "start_time": start.replace(tzinfo=None).isoformat(),
        "end_time": (start + timedelta(seconds=seconds))
        .replace(tzinfo=None)
        .isoformat(),
        "task_id": TASK_ID,
        "status_code": status,
        "raw_data": {"name": name, "attributes": attributes},
        "prompt_token_count": tokens,
        "completion_token_count": tokens,
        "total_token_count": 2 * tokens if tokens is not None else None,
        "prompt_token_cost": cost,
        "completion_token_cost": cost,
        "total_token_cost": 2 * cost if cost is not None else None,
    }


def _trace(
    trace_id: str,
    spans: list[dict[str, Any]],
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """A trace row, aggregated over every span the way the GenAI Engine stores it."""
    start = min(s["start_time"] for s in spans)
    end = max(s["end_time"] for s in spans)

    def total(key: str) -> Any:
        values = [s[key] for s in spans if s[key] is not None]
        return sum(values) if values else None

    return {
        "trace_id": trace_id,
        "task_id": TASK_ID,
        "user_id": user_id,
        "session_id": session_id,
        "start_time": start,
        "end_time": end,
        "span_count": len(spans),
        "duration_ms": (
            datetime.fromisoformat(end) - datetime.fromisoformat(start)
        ).total_seconds()
        * 1000,
        "prompt_token_count": total("prompt_token_count"),
        "completion_token_count": total("completion_token_count"),
        "total_token_count": total("total_token_count"),
        "prompt_token_cost": total("prompt_token_cost"),
        "completion_token_cost": total("completion_token_cost"),
        "total_token_cost": total("total_token_cost"),
        "spans": spans,
    }


def _validate_only_trace(start: datetime) -> dict[str, Any]:
    """What one validate call with no traceparent leaves: a trace whose root is GUARDRAIL."""
    trace_id = uuid.uuid4().hex
    prompt = _span(
        trace_id,
        "guardrail.validate_prompt",
        "GUARDRAIL",
        start,
        seconds=0.2,
    )
    response = _span(
        trace_id,
        "guardrail.validate_response",
        "GUARDRAIL",
        start + timedelta(seconds=1),
        seconds=0.2,
        parent=prompt["span_id"],
    )
    return _trace(trace_id, [prompt, response])


def _agent_trace(
    start: datetime,
    user: str = "user-1",
    session: str = "session-1",
    failed: bool = False,
) -> dict[str, Any]:
    trace_id = uuid.uuid4().hex
    root = _span(trace_id, "support_agent", "AGENT", start, seconds=4)
    llm = _span(
        trace_id,
        "ChatOpenAI",
        "LLM",
        start + timedelta(seconds=1),
        parent=root["span_id"],
        tokens=100,
        cost=0.01,
        model="gpt-4o",
    )
    tool = _span(
        trace_id,
        "lookup_order",
        "TOOL",
        start + timedelta(seconds=2),
        parent=root["span_id"],
        status="Error" if failed else "Ok",
    )
    return _trace(trace_id, [root, llm, tool], user_id=user, session_id=session)


def _days_ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


def _failed_result() -> OnboardingAnalysisResult:
    return OnboardingAnalysisResult(
        outcome=OnboardingOutcome.FAILED,
        error=OnboardingError(
            code=OnboardingErrorCode.INTERNAL,
            message="The analysis failed (ValueError).",
        ),
    )


class _Run:
    """One executor over a fake connector that returns `rows`, with a recording uploader."""

    def __init__(
        self,
        rows: list[dict[str, Any]],
        insight_client: Any = None,
    ) -> None:
        self.connector = MagicMock()
        self.connector.read_with_total_count.return_value = ConnectorReadResult(
            rows=rows,
            total_count=len(rows),
        )
        connector_constructor = MagicMock()
        connector_constructor.get_connector_from_spec.return_value = self.connector
        self.uploader = MagicMock()
        self.executor = OnboardingAnalysisExecutor(
            DatasetLoader(connector_constructor, MagicMock(), logger),
            self.uploader,
            logger,
            now=lambda: NOW,
            insight_client=insight_client,
        )
        self.job_id = str(uuid.uuid4())

    def __call__(self, **spec_fields: Any) -> OnboardingAnalysisResult:
        spec = OnboardingAnalysisJobSpec(
            connector_id="connector-1",
            address=OnboardingAddress(task_id=TASK_ID),
            **spec_fields,
        )
        result = self.executor.execute(self.job_id, "run-1", spec)
        self.uploader.upload.assert_called_once_with(self.job_id, "run-1", result)
        return result


def _loaded(rows: list[dict[str, Any]]) -> tuple[duckdb.DuckDBPyConnection, str]:
    """`rows` in DuckDB the way the executor loads them."""
    run = _Run(rows)
    conn = duckdb.connect()
    spec = OnboardingAnalysisJobSpec(
        connector_id="connector-1",
        address=OnboardingAddress(task_id=TASK_ID),
    )
    start, end = spec.window(NOW)
    table = run.executor._load_traces(conn, run.job_id, spec, start, end)
    return conn, table


GUARDRAIL_SPAN_NAMES = ["guardrail.validate_prompt", "guardrail.validate_response"]
AGENT_SPAN_NAMES = ["ChatOpenAI", "lookup_order", "support_agent"]


def _report(result: OnboardingAnalysisResult) -> OnboardingReport:
    assert result.report is not None
    return result.report


def _sample_table(
    rows: list[dict[str, Any]],
    salt: str = "job-1",
    **spec_fields: Any,
) -> duckdb.DuckDBPyConnection:
    """`rows` loaded as the executor loads them, with the sample drawn into `sample`."""
    conn, table = _loaded(rows)
    spec = OnboardingAnalysisJobSpec(
        connector_id="connector-1",
        address=OnboardingAddress(task_id=TASK_ID),
        **spec_fields,
    )
    _draw_sample(conn, table, "sample", spec, salt=salt)
    return conn


def _sampled_trace_ids(
    rows: list[dict[str, Any]],
    salt: str,
    **spec_fields: Any,
) -> set[str]:
    conn = _sample_table(rows, salt, **spec_fields)
    return {row[0] for row in conn.sql("SELECT trace_id FROM sample").fetchall()}


# --- Every trace counts ------------------------------------------------------------------


def test_validate_only_traces_proceed_past_the_minimum() -> None:
    # A validate-only agent: each validate call is a trace of its own, GUARDRAIL spans only.
    run = _Run([_validate_only_trace(_days_ago(i)) for i in range(15)])

    result = run(min_traces=10)

    assert result.outcome == OnboardingOutcome.COMPLETED
    report = _report(result)
    assert report.calls_validate is True
    assert report.span_names == GUARDRAIL_SPAN_NAMES
    assert report.totals.traces == 15
    assert report.sample is not None and report.sample.traces == 15


def test_a_mixed_trace_keeps_every_span_with_its_kind() -> None:
    trace_id = uuid.uuid4().hex
    start = _days_ago(1)
    root = _span(trace_id, "support_agent", "AGENT", start, seconds=2)
    llm = _span(
        trace_id,
        "ChatOpenAI",
        "LLM",
        start,
        parent=root["span_id"],
        tokens=100,
        cost=0.01,
    )
    # Validate called with this trace's traceparent.
    guardrail = _span(
        trace_id,
        "guardrail.validate_prompt",
        "GUARDRAIL",
        start,
        seconds=10,
        parent=root["span_id"],
    )

    conn = _sample_table([_trace(trace_id, [root, llm, guardrail])], min_traces=1)

    kinds, span_count, duration_ms, total_tokens = conn.sql(
        """
        SELECT list_transform(spans, s -> s.span_kind), span_count, duration_ms,
               total_token_count
        FROM sample
        """,
    ).fetchone()  # type: ignore[misc]
    # Every span reaches the sample, and its kind tells a GUARDRAIL span apart.
    assert kinds == ["AGENT", "LLM", "GUARDRAIL"]
    # The trace-level columns are the engine's, over every span.
    assert span_count == 3
    assert duration_ms == 10000.0
    assert total_tokens == 200


def test_a_span_with_no_kind_is_kept() -> None:
    rows = []
    for i in range(10):
        trace_id = uuid.uuid4().hex
        rows.append(
            _trace(trace_id, [_span(trace_id, "handle_request", None, _days_ago(i))])
        )
    run = _Run(rows)

    result = run(min_traces=10)

    assert result.outcome == OnboardingOutcome.COMPLETED
    report = _report(result)
    assert report.span_names == ["handle_request"]
    assert report.calls_validate is False
    assert report.sample is not None and report.sample.traces == 10
    sampled_kinds = (
        _sample_table(rows)
        .sql(
            "SELECT list_transform(spans, s -> s.span_kind) FROM sample",
        )
        .fetchall()
    )
    assert sampled_kinds == [([None],)] * 10


# --- Outcomes ----------------------------------------------------------------------------


def test_raw_data_disabled_does_not_stop_the_analysis() -> None:
    # The traces are analysed on this engine and only the result leaves it, so the
    # raw data setting, which guards data fetch jobs, does not apply.
    run = _Run([_agent_trace(_days_ago(1)) for _ in range(20)])

    with patch.object(Config, "settings") as settings:
        settings.as_dict.return_value = {"FETCH_RAW_DATA_ENABLED": "false"}
        result = run()

    assert result.outcome == OnboardingOutcome.COMPLETED
    run.connector.read_with_total_count.assert_called_once()
    assert _report(result).totals.traces == 20


def test_too_few_traces_ends_insufficient_traces_with_the_span_names_seen() -> None:
    rows = [_validate_only_trace(_days_ago(i)) for i in range(4)]
    rows += [_agent_trace(_days_ago(i)) for i in range(3)]
    run = _Run(rows)

    result = run(min_traces=10)

    assert result.outcome == OnboardingOutcome.INSUFFICIENT_TRACES
    report = _report(result)
    assert report.totals.traces == 7
    assert report.span_names == sorted(AGENT_SPAN_NAMES + GUARDRAIL_SPAN_NAMES)
    assert report.sample is None


def test_completed_counts_every_trace() -> None:
    rows = [_validate_only_trace(_days_ago(i % 30)) for i in range(30)]
    rows += [
        _agent_trace(
            _days_ago(i),
            user=f"user-{i % 4}",
            session=f"session-{i % 8}",
            failed=i % 5 == 0,
        )
        for i in range(20)
    ]
    run = _Run(rows)

    result = run()

    assert result.outcome == OnboardingOutcome.COMPLETED
    report = _report(result)
    assert report.calls_validate is True
    assert report.span_names == sorted(AGENT_SPAN_NAMES + GUARDRAIL_SPAN_NAMES)
    totals = report.totals
    assert totals.traces == 50
    # The validate-only fixtures carry no user or session.
    assert totals.sessions == 8
    assert totals.end_users == 4
    assert totals.error_rate == pytest.approx(4 / 50)
    # 30 traces at 1.2 s and 20 at 4 s: the 95th percentile falls among the 4 s ones.
    assert totals.p95_latency_ms == pytest.approx(4000.0)
    assert totals.token_cost == pytest.approx(20 * 0.02)
    assert sum(day.traces for day in totals.traces_per_day) == 50
    assert len(totals.traces_per_hour_avg) == 24
    assert sum(h.traces for h in totals.traces_per_hour_avg) == pytest.approx(50 / 30)
    assert totals.quietest_hour_utc == 0
    assert report.sample is not None and report.sample.traces == 50
    # No GenAI Engine to run the prompts: each insight is listed as skipped, never as
    # "nothing found".
    assert report.findings == []
    assert [(s.kind, s.reason) for s in report.skipped] == [
        ("rule_insights", INSIGHT_NOT_IMPLEMENTED),
        ("llm_insights", "engine_not_configured"),
    ]


def test_a_run_that_fails_uploads_a_failed_result_and_fails() -> None:
    run = _Run([])
    run.connector.read_with_total_count.side_effect = RuntimeError(
        "customer text from a trace"
    )
    spec = OnboardingAnalysisJobSpec(
        connector_id="connector-1",
        address=OnboardingAddress(task_id=TASK_ID),
    )

    with pytest.raises(RuntimeError):
        run.executor.execute(run.job_id, "run-1", spec)

    [(job_id, job_run_id, result)] = [
        c.args for c in run.uploader.upload.call_args_list
    ]
    assert (job_id, job_run_id) == (run.job_id, "run-1")
    assert result.outcome == OnboardingOutcome.FAILED
    assert result.report is None
    assert result.error is not None
    assert result.error.code == OnboardingErrorCode.INTERNAL
    # The type only: an exception's message can echo what was read.
    assert result.error.message == "The analysis failed (RuntimeError)."


def test_a_provider_project_is_not_read_yet() -> None:
    run = _Run([])
    spec = OnboardingAnalysisJobSpec(
        connector_id="connector-1",
        address=OnboardingAddress(provider_project="phoenix-project"),
    )

    with pytest.raises(NotImplementedError):
        run.executor.execute(run.job_id, "run-1", spec)

    run.connector.read_with_total_count.assert_not_called()
    [result] = [c.args[2] for c in run.uploader.upload.call_args_list]
    assert result.outcome == OnboardingOutcome.FAILED


def test_the_read_names_the_connector_task_and_window() -> None:
    run = _Run([])

    result = run()

    assert result.outcome == OnboardingOutcome.INSUFFICIENT_TRACES
    report = _report(result)
    assert report.totals.traces == 0
    assert report.totals.quietest_hour_utc is None
    dataset, start, end, filters, pagination = (
        run.connector.read_with_total_count.call_args.args
    )
    assert dataset.connector_id == "connector-1"
    assert dataset.model_problem_type == ModelProblemType.AGENTIC_TRACE
    assert {f.key: f.value for f in dataset.dataset_locator.fields} == {
        SHIELD_DATASET_TASK_ID_FIELD: TASK_ID,
    }
    assert (start, end) == (NOW - timedelta(days=30), NOW)
    assert (report.window.start, report.window.end) == (start, end)


# --- The sample --------------------------------------------------------------------------


def test_sample_is_capped_by_traces() -> None:
    run = _Run([_agent_trace(_days_ago(i * 0.5)) for i in range(40)])

    report = _report(run(sample_size=10))

    assert report.sample is not None and report.sample.traces == 10
    assert report.totals.traces == 40


def test_sample_is_capped_by_spans() -> None:
    # Three spans each: twelve spans fit four traces.
    conn = _sample_table(
        [_agent_trace(_days_ago(i * 0.5)) for i in range(40)],
        max_spans=12,
    )

    assert conn.sql("SELECT count(*), sum(span_count) FROM sample").fetchone() == (
        4,
        12,
    )


def test_spread_takes_from_every_slice_of_the_window() -> None:
    # Ten traces on each of six days, then forty more on the newest: `newest` would take
    # only from the last day, `spread` takes one from each.
    by_day = {
        day: [_agent_trace(_days_ago(day) + timedelta(minutes=i)) for i in range(10)]
        for day in range(6)
    }
    by_day[0] += [
        _agent_trace(_days_ago(0) + timedelta(minutes=30 + i)) for i in range(40)
    ]
    rows = [trace for traces in by_day.values() for trace in traces]
    ids_on = {day: {t["trace_id"] for t in traces} for day, traces in by_day.items()}

    spread = _sampled_trace_ids(rows, salt="job-1", sample_size=6)
    newest = _sampled_trace_ids(rows, salt="job-1", sample_size=6, sample="newest")

    assert [len(spread & ids_on[day]) for day in range(6)] == [1, 1, 1, 1, 1, 1]
    assert newest <= ids_on[0]


def test_the_same_job_draws_the_same_sample() -> None:
    rows = [_agent_trace(_days_ago(i * 0.25)) for i in range(80)]

    first = _sampled_trace_ids(rows, salt="job-1", sample_size=12)
    again = _sampled_trace_ids(rows, salt="job-1", sample_size=12)
    other_job = _sampled_trace_ids(rows, salt="job-2", sample_size=12)

    assert len(first) == 12
    assert first == again
    assert first != other_job


# --- The result and its upload -----------------------------------------------------------


def test_the_result_refuses_undeclared_fields() -> None:
    # As the Platform's model does: an undeclared field could carry trace content.
    with pytest.raises(ValidationError):
        SampleSummary(traces=1, trace_ids=["t1"])  # type: ignore[call-arg]


def test_the_result_matches_its_outcome() -> None:
    with pytest.raises(ValidationError):
        OnboardingAnalysisResult(outcome=OnboardingOutcome.COMPLETED)
    with pytest.raises(ValidationError):
        OnboardingAnalysisResult(outcome=OnboardingOutcome.FAILED)


def _unreachable_client() -> ApiClient:
    return ApiClient(Configuration(host="http://127.0.0.1:9"))


class _FakeResultBody:
    """Stands in for the client's PutOnboardingAnalysisResult: keeps the JSON it was
    built from."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "_FakeResultBody":
        return cls(data)


def test_the_upload_puts_the_result_on_this_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[ApiClient, dict[str, Any]]] = []

    class FakeOnboardingApi:
        def __init__(self, client: ApiClient) -> None:
            self.client = client

        def put_onboarding_analysis_result(self, **kwargs: Any) -> None:
            calls.append((self.client, kwargs))

    monkeypatch.setattr(
        api_bindings, "OnboardingV1Api", FakeOnboardingApi, raising=False
    )
    monkeypatch.setattr(
        api_bindings, "PutOnboardingAnalysisResult", _FakeResultBody, raising=False
    )
    client = _unreachable_client()
    result = _failed_result()

    PlatformOnboardingResultUploader(client).upload("job-1", "run-1", result)

    [(used_client, kwargs)] = calls
    assert used_client is client
    assert kwargs["job_id"] == "job-1"
    assert kwargs["job_run_id"] == "run-1"
    # The body is exactly the JSON the result dumps to, nothing added or dropped.
    assert kwargs["put_onboarding_analysis_result"].data == result.model_dump(
        mode="json"
    )


def test_a_result_the_client_rejects_is_not_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    put = MagicMock()

    class RejectingBody:
        @classmethod
        def from_dict(cls, data: dict[str, Any]) -> "RejectingBody":
            raise ValueError("field not declared")

    monkeypatch.setattr(
        api_bindings,
        "OnboardingV1Api",
        lambda client: MagicMock(put_onboarding_analysis_result=put),
        raising=False,
    )
    monkeypatch.setattr(
        api_bindings, "PutOnboardingAnalysisResult", RejectingBody, raising=False
    )
    result = _failed_result()

    with pytest.raises(OnboardingResultNotSent):
        PlatformOnboardingResultUploader(_unreachable_client()).upload(
            "job", "run", result
        )
    put.assert_not_called()


def test_a_result_not_sent_is_replaced_by_a_failed_one() -> None:
    run = _Run([])
    run.uploader.upload.side_effect = [OnboardingResultNotSent("ValueError"), None]
    spec = OnboardingAnalysisJobSpec(
        connector_id="connector-1",
        address=OnboardingAddress(task_id=TASK_ID),
    )

    with pytest.raises(OnboardingResultNotSent):
        run.executor.execute(run.job_id, "run-1", spec)

    first, second = [c.args[2] for c in run.uploader.upload.call_args_list]
    assert first.outcome == OnboardingOutcome.INSUFFICIENT_TRACES
    assert second.outcome == OnboardingOutcome.FAILED
    assert second.error is not None
    assert second.error.message == "The analysis failed (OnboardingResultNotSent)."


def test_a_failed_upload_after_a_failure_reaches_the_job_log_by_type_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    run = _Run([])
    run.uploader.upload.side_effect = ConnectionError("platform down")
    job_errors = MagicMock()
    run.executor.logger = MagicMock(error=job_errors)
    run.executor._analyse = MagicMock(  # type: ignore[method-assign]
        side_effect=ValueError("user jo@example.com said"),
    )
    spec = OnboardingAnalysisJobSpec(
        connector_id="connector-1",
        address=OnboardingAddress(task_id=TASK_ID),
    )

    with caplog.at_level(
        logging.ERROR,
        logger=onboarding_analysis_executor.engine_logger.name,
    ):
        with pytest.raises(ValueError):
            run.executor.execute(run.job_id, "run-1", spec)

    # The job's logger, whose errors go to the Platform: the upload error's type, and no
    # traceback, which would carry the analysis error as its context.
    [call] = job_errors.call_args_list
    assert "ConnectionError" in call.args[0]
    assert "exc_info" not in call.kwargs
    # The engine's own log keeps both.
    assert "jo@example.com" in caplog.text
    assert "platform down" in caplog.text


def test_a_finding_over_part_of_the_sample_says_so() -> None:
    verdict = MergedVerdict(
        kind="tool_failures",
        fired="yes",
        matched_trace_ids=[f"trace-{i}" for i in range(9)],
        example_span_name=None,
        reasons=["Tools failed."],
        suggested_check=None,
        traces_answered=105,
    )

    finding = _finding(verdict, sampled=473)

    assert finding.title == (
        "Tool failures: yes, in 9 of 105 traces analysed (473 sampled)"
    )
    assert finding.values == {
        "fired": 1.0,
        "traces_matched": 9.0,
        "traces_in_sample": 105.0,
        "traces_sampled": 473.0,
    }
    # The Platform shows findings to the customer, so they carry counts, not trace ids.
    assert "trace-" not in finding.title
    assert finding.detail is not None and "trace-" not in finding.detail


def test_a_window_start_without_an_offset_is_read_as_utc() -> None:
    spec = OnboardingAnalysisJobSpec.model_validate(
        {
            "connector_id": "connector-1",
            "address": {"task_id": TASK_ID},
            "start_timestamp": "2026-11-10T00:00:00",
        },
    )

    start, end = spec.window(NOW)

    assert start == datetime(2026, 11, 10, tzinfo=timezone.utc)
    assert end - start == timedelta(days=7, hours=12)


def test_a_client_without_the_route_cannot_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(api_bindings, "OnboardingV1Api", raising=False)
    result = _failed_result()
    with pytest.raises(NotImplementedError, match="onboarding result route"):
        PlatformOnboardingResultUploader(_unreachable_client()).upload(
            "job", "run", result
        )


@pytest.mark.skipif(
    not ONBOARDING_ANALYSIS_SUPPORTED,
    reason="this arthur-client cannot run onboarding analysis jobs",
)
def test_a_completed_result_is_a_valid_platform_upload() -> None:
    # The Platform refuses any field it does not declare. Building the client's own
    # body model from a real run's result checks the two sides still agree.
    rows = [
        _agent_trace(_days_ago(i), user=f"user-{i % 4}", session=f"session-{i % 8}")
        for i in range(20)
    ]
    result = _Run(rows)()
    assert result.outcome == OnboardingOutcome.COMPLETED

    body = api_bindings.PutOnboardingAnalysisResult.from_dict(
        result.model_dump(mode="json")
    )

    assert body.outcome.value == "completed"
    assert body.report.totals.traces == 20
    assert body.report.span_names == _report(result).span_names
    assert [s.kind for s in body.report.skipped] == ["rule_insights", "llm_insights"]


@pytest.mark.skipif(
    not ONBOARDING_ANALYSIS_SUPPORTED,
    reason="this arthur-client cannot run onboarding analysis jobs",
)
def test_the_engine_does_not_take_jobs_it_cannot_upload() -> None:
    # The engine declares on dequeue that it runs these jobs as soon as its client can,
    # so with such a client the upload must reach the transport as the route's PUT: the
    # generated API and body model run, only the transport is a stub.
    transport = MagicMock(wraps=_unreachable_client())
    transport.call_api = MagicMock()
    transport.response_deserialize = MagicMock()
    result = _failed_result()

    PlatformOnboardingResultUploader(transport).upload("job", "run", result)

    method, url, *_ = transport.call_api.call_args.args
    assert method == "PUT"
    assert url.endswith("/api/v1/jobs/job/runs/run/onboarding_result")


# --- What reaches the wizard ---------------------------------------------------------------


def test_a_malformed_spec_uploads_a_failed_result_and_fails() -> None:
    run = _Run([])
    # No connector_id, and min_traces not a number: the spec as the Platform sent it.
    raw_spec = {"address": {"task_id": TASK_ID}, "min_traces": "ten"}

    with pytest.raises(ValidationError):
        run.executor.execute(run.job_id, "run-1", raw_spec)

    run.connector.read_with_total_count.assert_not_called()
    [result] = [c.args[2] for c in run.uploader.upload.call_args_list]
    assert result.outcome == OnboardingOutcome.FAILED
    assert result.error is not None
    assert result.error.message == "The analysis failed (ValidationError)."


def test_span_names_stay_within_the_platform_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(onboarding_analysis_executor, "MAX_SPAN_NAMES", 2)
    too_long = "x" * (onboarding_analysis_executor.MAX_SPAN_NAME_LENGTH + 1)
    rows = []
    for i in range(10):
        trace_id = uuid.uuid4().hex
        spans = [_span(trace_id, "frequent", "CHAIN", _days_ago(i))]
        spans.append(_span(trace_id, too_long, "CHAIN", _days_ago(i)))
        if i < 5:
            spans.append(_span(trace_id, "common", "CHAIN", _days_ago(i)))
        if i == 0:
            spans.append(_span(trace_id, "aaa_rare", "CHAIN", _days_ago(i)))
        rows.append(_trace(trace_id, spans))

    report = _report(_Run(rows)(min_traces=1))

    # The most frequent names that fit, never one the Platform would refuse.
    assert report.span_names == ["common", "frequent"]


class _NoModelEngine:
    """A GenAI Engine with no default model, which records the job summary it is sent."""

    def __init__(self) -> None:
        self.summaries: list[dict[str, Any]] = []

    def default_model(self) -> None:
        return None

    def run_prompt(self, prompt_name: str, traces_text: str) -> Any:
        raise AssertionError("no prompt runs without a default model")

    def report_session(self, summary: dict[str, Any]) -> None:
        self.summaries.append(summary)


def test_the_job_reports_its_steps_and_result_for_its_trace() -> None:
    engine = _NoModelEngine()
    rows = [_agent_trace(_days_ago(i)) for i in range(12)]

    result = _Run(rows, insight_client=engine)()

    [summary] = engine.summaries
    assert summary["status"] == "ok"
    assert [s["name"] for s in summary["steps"]] == [
        "read_traces",
        "sample",
        "llm_insights",
    ]
    assert summary["steps"][0]["attributes"] == {"traces": 12}
    assert summary["input"] == {
        "agent_task_id": TASK_ID,
        "connector_id": "connector-1",
        "sample_size": 500,
    }
    assert summary["output"]["outcome"] == result.outcome.value == "completed"
    assert summary["output"]["traces_read"] == 12
    assert "llm_insights: default_model_not_configured" in summary["output"]["skipped"]
    # Counts and verdicts only: nothing read from the traces.
    assert set(summary["output"]) == {
        "outcome",
        "traces_read",
        "findings",
        "skipped",
        "llm_calls",
        "cost_usd",
    }


def test_a_summary_that_cannot_be_sent_does_not_fail_the_job() -> None:
    engine = _NoModelEngine()
    engine.report_session = MagicMock(side_effect=ConnectionError())  # type: ignore[method-assign]
    rows = [_agent_trace(_days_ago(i)) for i in range(12)]

    result = _Run(rows, insight_client=engine)()

    assert result.outcome == OnboardingOutcome.COMPLETED
