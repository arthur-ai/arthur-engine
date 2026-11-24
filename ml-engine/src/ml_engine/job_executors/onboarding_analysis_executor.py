"""Executor for the ONBOARDING_ANALYSIS job: the trace analysis behind onboarding.

The job runs before the application exists, so it loads no model and computes, uploads
or queues no metrics. It reads the agent's recent traces through the connector the job
names, into DuckDB through the loader the metrics job uses, and hands one result back:

1. Raw data check. An engine with FETCH_RAW_DATA_ENABLED off has said that no trace
   content may leave it, so the job reads nothing and ends `raw_data_disabled`.
2. Read the window (the last 30 days unless the spec says otherwise) into DuckDB.
3. Below `min_traces` traces, end `insufficient_traces`, still with the totals and the
   span names seen, so transforms can be built.
4. Totals by SQL.
5. Sample up to `sample_size` traces and `max_spans` spans, drawn in DuckDB.
6. Insights. With a GenAI Engine configured, the LLM insights send the sampled traces
   to its saved insight prompts (`onboarding_insights`) and report a finding per insight.
   The rule insights are not built yet. An insight that does not run is listed in
   `skipped` with the reason, never reported as "nothing found".
7. Upload the one result.

Every trace read counts and is analysed, GUARDRAIL spans included. A validate call made
without a traceparent opens a trace of its own whose only spans are GUARDRAIL ones, and
such a span holds the text checked as its input, the user and session, and the rule
results as its output: a validate-only agent has real traces to analyse, though no tool
or retrieval spans. Each span keeps its `span_kind`, so a later step can tell them apart.

The job spec is modelled here, because the pinned arthur-client predates the kind. The
upload goes through `OnboardingResultUploader`; its Platform implementation looks the
result route up in the installed client when it runs, so this module still loads under a
client without it, and the engine declares the kind on dequeue only when it is there.
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Literal, Protocol, Self

import arthur_client.api_bindings as api_bindings
import duckdb
from arthur_client.api_bindings import (
    ApiClient,
    AvailableDataset,
    DatasetLocator,
    DatasetLocatorField,
)
from arthur_client.api_bindings import DatasetSchema as ClientDatasetSchema
from arthur_client.api_bindings import ModelProblemType as ClientModelProblemType
from arthur_common.models.connectors import SHIELD_DATASET_TASK_ID_FIELD
from arthur_common.models.schema_definitions import AGENTIC_TRACE_SCHEMA
from arthur_common.tools.duckdb_data_loader import DuckDBOperator
from duckdb import DuckDBPyConnection
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from arthur_client_support import (
    ONBOARDING_RESULT_API,
    ONBOARDING_RESULT_METHOD,
    ONBOARDING_RESULT_MODEL,
)
from config import Config
from dataset_loader import DatasetLoader
from job_executors.onboarding_insights import (
    InsightEngineClient,
    InsightSpan,
    MergedVerdict,
    run_llm_insights,
)
from tools.converters import client_to_common_dataset_schema

ONBOARDING_WINDOW = timedelta(days=30)

# The OpenInference span kind the GenAI Engine gives the span around a validate call.
GUARDRAIL_SPAN_KIND = "GUARDRAIL"

# Where the sample drawn from the traces read lives in DuckDB.
SAMPLE_TABLE = "onboarding_sample"

# `spread` cuts the window that came back into this many time slices.
SPREAD_SLICES = 6

# The reason an insight is listed in `skipped` while the insight steps are not built.
INSIGHT_NOT_IMPLEMENTED = "not_implemented"

# The Platform's bounds on `span_names`: it refuses an upload with more names, or with a
# longer one. A transform matches a span by its exact name, so a name too long to send
# is dropped rather than cut, and past the count the most frequent names are kept.
MAX_SPAN_NAMES = 2000
MAX_SPAN_NAME_LENGTH = 512


class OnboardingAddress(BaseModel):
    """Where the traces are, on the source side: a GenAI Engine task, or a provider's
    project. The Platform sets exactly one."""

    task_id: str | None = None
    provider_project: str | None = None


class OnboardingAnalysisJobSpec(BaseModel):
    """The ONBOARDING_ANALYSIS job spec, until arthur-client publishes its own.

    The caps live here, not on the connector, because scheduled metrics runs reuse the
    same connector uncapped.
    """

    connector_id: str
    address: OnboardingAddress
    start_timestamp: datetime | None = None
    end_timestamp: datetime | None = None
    min_traces: int = Field(default=10, ge=1)
    sample_size: int = Field(default=500, ge=1)
    sample: Literal["spread", "newest"] = "spread"
    # TODO: bound the read by `max_root_spans` and mark the totals `lower_bound` when it
    # stops there. The loader's single-page read cannot express it: a 100,000-row page is
    # far over the GenAI Engine's page size limit.
    max_root_spans: int = Field(default=100_000, ge=1)
    max_spans: int = Field(default=10_000, ge=1)

    @field_validator("start_timestamp", "end_timestamp")
    @classmethod
    def _utc_if_naive(cls, value: datetime | None) -> datetime | None:
        # The window's other end may be the engine's aware clock, and the two are
        # subtracted: a timestamp without an offset is read as UTC.
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def window(self, now: datetime) -> tuple[datetime, datetime]:
        end = self.end_timestamp or now
        start = self.start_timestamp or end - ONBOARDING_WINDOW
        return start, end


# The result below mirrors the Platform's `PutOnboardingAnalysisResult`, which refuses
# any field it does not declare: the result is saved on the Platform, and an undeclared
# field is the easiest way for trace content to reach it. A field added here must be
# added there first.


class _EngineReport(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OnboardingOutcome(str, Enum):
    COMPLETED = "completed"
    INSUFFICIENT_TRACES = "insufficient_traces"
    RAW_DATA_DISABLED = "raw_data_disabled"
    FAILED = "failed"
    LLM_INSIGHTS_OFF = "llm_insights_off"


class OnboardingErrorCode(str, Enum):
    PROVIDER_ERROR = "provider_error"
    INTERNAL = "internal"


class OnboardingError(_EngineReport):
    code: OnboardingErrorCode
    message: str


class AnalysisWindow(_EngineReport):
    start: datetime
    end: datetime


class TracesOnDay(_EngineReport):
    date: date
    traces: int


class TracesInHour(_EngineReport):
    hour_utc: int
    traces: float


class Totals(_EngineReport):
    """Counts over every trace read in the window."""

    basis: Literal["window"] = "window"
    traces: int
    sessions: int
    end_users: int
    error_rate: float | None
    p95_latency_ms: float | None
    token_cost: float | None
    # TODO: the currency the engine reports; agentic data retrieval does not carry it yet,
    # and the analysis must never assume USD.
    currency: str | None = None
    traces_per_day: list[TracesOnDay]
    traces_per_hour_avg: list[TracesInHour]
    quietest_hour_utc: int | None


class SampleSummary(_EngineReport):
    basis: Literal["sample"] = "sample"
    traces: int


class Finding(_EngineReport):
    kind: str
    title: str
    detail: str | None = None
    basis: Literal["window", "sample"]
    values: dict[str, float] = Field(default_factory=dict)


class SkippedInsight(_EngineReport):
    kind: str
    reason: str


class OnboardingReport(_EngineReport):
    """The facts a run found. Nothing here is trace content."""

    window: AnalysisWindow
    totals: Totals
    sample: SampleSummary | None = None
    calls_validate: bool | None = None
    span_names: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    skipped: list[SkippedInsight] = Field(default_factory=list)
    baselines: dict[str, dict[str, dict[str, float]]] = Field(default_factory=dict)


class OnboardingAnalysisResult(_EngineReport):
    """The one result a run uploads: how it ended, and what it found unless it read
    nothing."""

    outcome: OnboardingOutcome
    error: OnboardingError | None = None
    report: OnboardingReport | None = None

    @model_validator(mode="after")
    def matches_outcome(self) -> Self:
        failed = self.outcome == OnboardingOutcome.FAILED
        if failed != (self.error is not None):
            raise ValueError("error is set when, and only when, outcome is failed.")
        read_nothing = self.outcome in (
            OnboardingOutcome.FAILED,
            OnboardingOutcome.RAW_DATA_DISABLED,
        )
        if read_nothing != (self.report is None):
            raise ValueError(
                f"A {self.outcome.value} result {'carries no' if read_nothing else 'needs a'} report.",
            )
        return self


class OnboardingResultUploader(Protocol):
    def upload(
        self,
        job_id: str,
        job_run_id: str,
        result: OnboardingAnalysisResult,
    ) -> None: ...


class OnboardingResultNotSent(Exception):
    """The result could not be prepared for upload, so nothing reached the Platform for
    this attempt and a failed result may still be sent in its place."""


class OnboardingAnalysisFailed(Exception):
    """An onboarding analysis failed. Names only the original exception's type: the
    job's logger sends what it logs to the Platform, and a message can quote the traces.
    """


class PlatformOnboardingResultUploader:
    """Uploads the result to the Platform's onboarding result route for this attempt:
    PUT /api/v1/jobs/{job_id}/runs/{job_run_id}/onboarding_result.

    Only the engine the job was handed to may call it. An identical upload for the same
    attempt is a no-op there and a different one is a 409, so a retried call is safe.

    The route and its body model are looked up in the installed client when the upload
    runs, not imported: the pinned client predates them, and this module is imported at
    engine start whatever the client.
    """

    def __init__(self, api_client: ApiClient) -> None:
        self.api_client = api_client

    def upload(
        self,
        job_id: str,
        job_run_id: str,
        result: OnboardingAnalysisResult,
    ) -> None:
        result_api = getattr(api_bindings, ONBOARDING_RESULT_API, None)
        body_model = getattr(api_bindings, ONBOARDING_RESULT_MODEL, None)
        if result_api is None or body_model is None:
            raise NotImplementedError(
                "This engine's arthur-client has no onboarding result route; "
                "the onboarding analysis result cannot be uploaded.",
            )
        # The client's model is built from the same JSON the Platform receives, so a
        # field the Platform does not declare fails here, before anything is sent.
        try:
            body = body_model.from_dict(result.model_dump(mode="json"))
        except Exception as e:
            raise OnboardingResultNotSent(type(e).__name__) from e
        getattr(result_api(self.api_client), ONBOARDING_RESULT_METHOD)(
            job_id=job_id,
            job_run_id=job_run_id,
            put_onboarding_analysis_result=body,
        )


class OnboardingAnalysisExecutor:
    def __init__(
        self,
        dataset_loader: DatasetLoader,
        uploader: OnboardingResultUploader,
        logger: logging.Logger,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        insight_client: InsightEngineClient | None = None,
    ) -> None:
        self.dataset_loader = dataset_loader
        self.uploader = uploader
        self.logger = logger
        self.now = now
        # The GenAI Engine that runs the insight prompts; None when this engine has none
        # configured, which skips the LLM insights.
        self.insight_client = insight_client

    def execute(
        self,
        job_id: str,
        job_run_id: str,
        spec: OnboardingAnalysisJobSpec | dict[str, Any],
    ) -> OnboardingAnalysisResult:
        """Run the analysis and upload its result.

        `spec` may be the job spec as the Platform sent it: it is validated here, so a
        malformed one is also reported to the wizard as a failed result.
        """
        try:
            result = self._analyse(
                job_id,
                OnboardingAnalysisJobSpec.model_validate(spec),
            )
        except Exception as e:
            self._report_failure(job_id, job_run_id, e)
            raise
        self.logger.info(f"Onboarding analysis {job_id} ended {result.outcome.value}")
        try:
            self.uploader.upload(job_id, job_run_id, result)
        except OnboardingResultNotSent as e:
            # Nothing was sent for this attempt. After a send that failed the Platform
            # may hold the result already, so only this case reports a different one.
            self._report_failure(job_id, job_run_id, e)
            raise
        return result

    def _report_failure(self, job_id: str, job_run_id: str, error: Exception) -> None:
        """Best effort: tell the wizard the run failed, so it need not wait out its timeout.

        The message names the exception type only: a message can echo what was read.
        """
        # TODO: report a source or model provider that refused or failed as
        # `provider_error`, once the read and the insight calls say which they were.
        result = OnboardingAnalysisResult(
            outcome=OnboardingOutcome.FAILED,
            error=OnboardingError(
                code=OnboardingErrorCode.INTERNAL,
                message=f"The analysis failed ({type(error).__name__}).",
            ),
        )
        try:
            self.uploader.upload(job_id, job_run_id, result)
        except Exception:
            self.logger.error(
                f"Could not upload the failed result of onboarding analysis {job_id}",
                exc_info=True,
            )

    def _analyse(
        self,
        job_id: str,
        spec: OnboardingAnalysisJobSpec,
    ) -> OnboardingAnalysisResult:
        start, end = spec.window(self.now())
        window = AnalysisWindow(start=start, end=end)

        if not Config.get_bool("FETCH_RAW_DATA_ENABLED", default=True):
            self.logger.info(
                "Raw data access is disabled for this engine, so no traces are read for onboarding analysis.",
            )
            return OnboardingAnalysisResult(outcome=OnboardingOutcome.RAW_DATA_DISABLED)

        conn = duckdb.connect()
        try:
            traces_table = self._load_traces(conn, job_id, spec, start, end)
            calls_validate = _calls_validate(conn, traces_table)
            span_names = _span_names(conn, traces_table)
            totals = _totals(conn, traces_table, start, end)
            self.logger.info(f"Read {totals.traces} traces for onboarding analysis.")

            if totals.traces < spec.min_traces:
                return OnboardingAnalysisResult(
                    outcome=OnboardingOutcome.INSUFFICIENT_TRACES,
                    report=OnboardingReport(
                        window=window,
                        totals=totals,
                        calls_validate=calls_validate,
                        span_names=span_names,
                    ),
                )

            sample = _draw_sample(conn, traces_table, SAMPLE_TABLE, spec, salt=job_id)
            findings, skipped, insights_off = self._insights(conn, SAMPLE_TABLE)
            return OnboardingAnalysisResult(
                outcome=(
                    OnboardingOutcome.LLM_INSIGHTS_OFF
                    if insights_off
                    else OnboardingOutcome.COMPLETED
                ),
                report=OnboardingReport(
                    window=window,
                    totals=totals,
                    sample=sample,
                    calls_validate=calls_validate,
                    span_names=span_names,
                    findings=findings,
                    skipped=skipped,
                ),
            )
        finally:
            conn.close()

    def _load_traces(
        self,
        conn: DuckDBPyConnection,
        job_id: str,
        spec: OnboardingAnalysisJobSpec,
        start: datetime,
        end: datetime,
    ) -> str:
        dataset = trace_dataset(job_id, spec)
        table = self.dataset_loader.load_physical_dataset(conn, dataset, start, end)
        # The loader leaves every column named by its schema column id; restore the source
        # names, as load_datasets does after loading, so the SQL here reads `spans`.
        assert dataset.dataset_schema is not None
        DuckDBOperator.apply_alias_mask(
            table_name=table,
            conn=conn,
            schema=client_to_common_dataset_schema(dataset.dataset_schema),
        )
        return table

    def _insights(
        self,
        conn: DuckDBPyConnection,
        sample_table: str,
    ) -> tuple[list[Finding], list[SkippedInsight], bool]:
        """The findings, the insights that could not run, and whether the insights
        setting is off."""
        # TODO: rule insights over the sample, no LLM, and the PII detector.
        skipped = [SkippedInsight(kind="rule_insights", reason=INSIGHT_NOT_IMPLEMENTED)]
        if self.insight_client is None:
            skipped.append(
                SkippedInsight(kind="llm_insights", reason="engine_not_configured"),
            )
            return [], skipped, False
        traces = _sampled_traces(conn, sample_table)
        run = run_llm_insights(self.insight_client, traces, self.logger)
        skipped += [SkippedInsight(kind=k, reason=r) for k, r in run.skipped]
        findings = [_finding(v, sample_traces=run.traces) for v in run.verdicts]
        return findings, skipped, run.insights_off


# What the title calls each insight.
INSIGHT_TITLES = {
    "internet_access": "Internet access",
    "tool_output_to_llm": "Tool output reaches the model",
    "reference_material": "Reference material",
    "user_facing": "User-facing",
    "heavy_model": "Heavy model for light work",
    "tool_failures": "Tool failures",
}
MAX_TITLE_LENGTH = 300
MAX_DETAIL_LENGTH = 2000
MAX_TRACE_IDS_IN_DETAIL = 10


def _finding(verdict: MergedVerdict, sample_traces: int) -> Finding:
    """An insight's verdict in the Platform's finding shape.

    `values["fired"]` is 1 for yes and 0 for no, and absent when the model could not
    tell, which the title says. Trace ids, the example span and the suggested check are
    text, so they go in `detail`, which the Platform keeps to 2,000 characters.
    """
    matched = len(verdict.matched_trace_ids)
    label = INSIGHT_TITLES.get(verdict.kind, verdict.kind)
    if verdict.fired == "yes":
        title = f"{label}: yes, in {matched} of {sample_traces} sampled traces"
    elif verdict.fired == "no":
        title = f"{label}: no, in {sample_traces} sampled traces"
    else:
        title = f"{label}: cannot tell from {sample_traces} sampled traces"
    parts = [" ".join(verdict.reasons)]
    if verdict.example_span_name:
        parts.append(f"Example span: {verdict.example_span_name}.")
    if verdict.suggested_check:
        parts.append(f"Suggested: {verdict.suggested_check}.")
    if verdict.matched_trace_ids:
        shown = verdict.matched_trace_ids[:MAX_TRACE_IDS_IN_DETAIL]
        more = matched - len(shown)
        parts.append(
            "Matched traces: "
            + ", ".join(shown)
            + (f" and {more} more." if more else "."),
        )
    values = {
        "traces_matched": float(matched),
        "traces_in_sample": float(sample_traces),
    }
    if verdict.fired in ("yes", "no"):
        values["fired"] = 1.0 if verdict.fired == "yes" else 0.0
    # TODO: scrub personal data from the model's reasons in the GenAI Engine before
    # they leave it, as the design requires of free text.
    return Finding(
        kind=verdict.kind,
        title=title[:MAX_TITLE_LENGTH],
        detail=" ".join(p for p in parts if p)[:MAX_DETAIL_LENGTH] or None,
        basis="sample",
        values=values,
    )


def _sampled_traces(
    conn: DuckDBPyConnection,
    sample_table: str,
) -> dict[str, list[InsightSpan]]:
    """The sampled traces' spans, keyed by trace id, in the sample's time order."""
    rows = conn.sql(
        f"SELECT trace_id, spans FROM {sample_table} ORDER BY start_time, trace_id",
    ).fetchall()
    traces: dict[str, list[InsightSpan]] = {}
    for trace_id, spans in rows:
        traces[trace_id] = [
            InsightSpan(
                span_id=s["span_id"],
                parent_span_id=s["parent_span_id"],
                span_kind=s["span_kind"],
                span_name=s["span_name"],
                status_code=s["status_code"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                raw_data=_json_value(s["raw_data"]),
                session_id=s["session_id"],
            )
            for s in spans or []
        ]
    return traces


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def trace_dataset(job_id: str, spec: OnboardingAnalysisJobSpec) -> AvailableDataset:
    """The traces to read, as the loader takes them.

    There is no Platform dataset before the application exists, so this one is built in
    memory from the job spec. The job id names the DuckDB table. The read path uses no
    project or data plane, and the job has neither, so they are left empty.
    """
    if spec.address.task_id is None:
        # TODO: read a provider's project through its connector.
        raise NotImplementedError(
            "Onboarding analysis reads only traces in a GenAI Engine task so far.",
        )
    now = datetime.now(timezone.utc)
    return AvailableDataset(
        id=job_id,
        created_at=now,
        updated_at=now,
        connector_id=spec.connector_id,
        project_id="",
        data_plane_id="",
        name="onboarding traces",
        # TODO: a provider connector's address (its project, not a task id) once one is
        # wired up; the locator key here is the GenAI Engine's.
        dataset_locator=DatasetLocator(
            fields=[
                DatasetLocatorField(
                    key=SHIELD_DATASET_TASK_ID_FIELD,
                    value=spec.address.task_id,
                ),
            ],
        ),
        dataset_schema=ClientDatasetSchema.from_dict(
            AGENTIC_TRACE_SCHEMA().model_dump(mode="json"),
        ),
        model_problem_type=ClientModelProblemType.AGENTIC_TRACE,
        is_static=False,
    )


def _one(conn: DuckDBPyConnection, query: str) -> tuple[Any, ...]:
    row = conn.sql(query).fetchone()
    if row is None:
        raise ValueError(f"Expected one row from: {query}")
    return row


def _calls_validate(conn: DuckDBPyConnection, table: str) -> bool:
    """Whether any trace holds a GUARDRAIL span, which only a validate call makes."""
    (calls,) = _one(
        conn,
        f"""
        SELECT coalesce(bool_or(len(list_filter(spans, s -> s.span_kind = '{GUARDRAIL_SPAN_KIND}')) > 0), false)
        FROM {table}
        """,
    )
    return bool(calls)


def _span_names(conn: DuckDBPyConnection, table: str) -> list[str]:
    """The distinct span names seen, within the Platform's bounds, sorted."""
    rows = conn.execute(
        f"""
        SELECT s.span_name
        FROM (SELECT unnest(spans) AS s FROM {table})
        WHERE s.span_name IS NOT NULL AND length(s.span_name) <= $max_length
        GROUP BY s.span_name
        ORDER BY count(*) DESC, s.span_name
        LIMIT $max_names
        """,
        {"max_length": MAX_SPAN_NAME_LENGTH, "max_names": MAX_SPAN_NAMES},
    ).fetchall()
    return sorted(row[0] for row in rows)


def _totals(
    conn: DuckDBPyConnection,
    table: str,
    start: datetime,
    end: datetime,
) -> Totals:
    (
        traces,
        sessions,
        end_users,
        error_rate,
        p95_latency_ms,
        token_cost,
    ) = _one(
        conn,
        f"""
        SELECT count(*),
               count(DISTINCT session_id),
               count(DISTINCT user_id),
               avg(CASE WHEN len(list_filter(spans, s -> s.status_code = 'Error')) > 0
                        THEN 1.0 ELSE 0.0 END),
               quantile_cont(duration_ms, 0.95),
               sum(total_token_cost)
        FROM {table}
        """,
    )
    traces_per_day = [
        TracesOnDay(date=row[0], traces=row[1])
        for row in conn.sql(
            f"""
            SELECT CAST(start_time AS DATE) AS day, count(*)
            FROM {table}
            GROUP BY day
            ORDER BY day
            """,
        ).fetchall()
    ]
    window_days = max((end - start).total_seconds() / 86400, 1.0)
    traces_per_hour_avg = [
        TracesInHour(hour_utc=row[0], traces=row[1] / window_days)
        for row in conn.sql(
            f"""
            SELECT CAST(h.hour_utc AS INTEGER), count(t.start_time)
            FROM range(24) AS h(hour_utc)
            LEFT JOIN {table} AS t ON hour(t.start_time) = h.hour_utc
            GROUP BY h.hour_utc
            ORDER BY h.hour_utc
            """,
        ).fetchall()
    ]
    quietest_hour_utc = (
        min(traces_per_hour_avg, key=lambda h: (h.traces, h.hour_utc)).hour_utc
        if traces
        else None
    )
    return Totals(
        traces=traces,
        sessions=sessions,
        end_users=end_users,
        error_rate=error_rate,
        p95_latency_ms=p95_latency_ms,
        token_cost=token_cost,
        traces_per_day=traces_per_day,
        traces_per_hour_avg=traces_per_hour_avg,
        quietest_hour_utc=quietest_hour_utc,
    )


def _draw_sample(
    conn: DuckDBPyConnection,
    source_table: str,
    target_table: str,
    spec: OnboardingAnalysisJobSpec,
    salt: str,
) -> SampleSummary:
    """Copy up to `sample_size` traces and `max_spans` spans of `source_table` to `target_table`.

    `spread` cuts the window that came back into `SPREAD_SLICES` time slices and takes
    traces from each in turn, in a random order within each slice, so an empty slice's
    share goes to the others. `newest` takes the newest traces. The order is a hash of the
    trace id and `salt`, so the same job draws the same sample. Traces are taken in that
    order until the next would pass `max_spans`; a trace larger than `max_spans` on its
    own is never taken.
    """
    if spec.sample == "spread":
        pick_order = "row_number() OVER (ORDER BY rank_in_slice, slice)"
    else:
        pick_order = "row_number() OVER (ORDER BY start_time DESC, trace_id)"
    conn.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE {target_table} AS
        WITH bounds AS (
            SELECT epoch(min(start_time)) AS lo, epoch(max(start_time)) AS hi
            FROM {source_table}
        ),
        sliced AS (
            SELECT t.*,
                   least(
                       CAST(floor((epoch(t.start_time) - b.lo)
                                  / greatest(b.hi - b.lo, 1e-9) * {SPREAD_SLICES}) AS BIGINT),
                       {SPREAD_SLICES - 1}
                   ) AS slice
            FROM {source_table} AS t, bounds AS b
            WHERE t.span_count <= $max_spans
        ),
        ranked AS (
            SELECT *,
                   row_number() OVER (PARTITION BY slice ORDER BY hash(trace_id || $salt))
                       AS rank_in_slice
            FROM sliced
        ),
        picked AS (
            SELECT *, {pick_order} AS pick_order FROM ranked
        ),
        capped AS (
            SELECT *,
                   sum(span_count) OVER (ORDER BY pick_order ROWS UNBOUNDED PRECEDING)
                       AS spans_so_far
            FROM picked
            WHERE pick_order <= $sample_size
        )
        SELECT * EXCLUDE (slice, rank_in_slice, pick_order, spans_so_far)
        FROM capped
        WHERE spans_so_far <= $max_spans
        """,
        {
            "max_spans": spec.max_spans,
            "sample_size": spec.sample_size,
            "salt": salt,
        },
    )
    (traces,) = _one(conn, f"SELECT count(*) FROM {target_table}")
    return SampleSummary(traces=traces)
