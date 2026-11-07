from datetime import datetime, timedelta
from typing import Any, List, Optional

from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from schemas.common_schemas import ContinuousEvalTraceFilterCondition
from schemas.enums import SpendEstimateUnavailableReason
from schemas.internal_schemas import ContinuousEval
from schemas.response_schemas import (
    ContinuousEvalDailySpendEstimate,
    ContinuousEvalSpendResponse,
)
from utils.constants import AGENT_EXPERIMENT_SESSION_PREFIX
from utils.transform_executor import spans_match_filter

SPEND_ESTIMATE_WINDOW_DAYS = 7
# A new eval's trace filter is tried on at most this many of the task's latest
# traces, so the create-form estimate stays a bounded read.
FILTER_SHARE_MAX_TRACES = 200

# Runs that reached the LLM. Pending and running runs have no cost yet, skipped
# runs never call it, and errored runs may have failed before or during the call.
_LLM_CALLING_RUN_STATUSES = (
    ContinuousEvalRunStatus.PASSED.value,
    ContinuousEvalRunStatus.FAILED.value,
)


class ContinuousEvalSpendRepository:
    """Read-only spend figures for continuous evals, from their live runs."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_continuous_eval_spend(
        self,
        continuous_eval: ContinuousEval,
        now: Optional[datetime] = None,
    ) -> ContinuousEvalSpendResponse:
        now = now or datetime.now()
        day_start = now - timedelta(days=1)
        window_start = now - timedelta(days=SPEND_ESTIMATE_WINDOW_DAYS)
        cost = func.coalesce(DatabaseAgenticAnnotation.cost, 0.0)
        in_last_day = DatabaseAgenticAnnotation.created_at >= day_start

        # One range scan over ix_agentic_annotations_continuous_eval_created
        # covers both the last day and the estimate window.
        row = (
            self.db_session.query(
                func.count(case((in_last_day, 1))).label("day_run_count"),
                func.coalesce(func.sum(case((in_last_day, cost))), 0.0).label(
                    "day_cost",
                ),
                *self._average_run_cost_columns(cost),
            )
            .filter(
                DatabaseAgenticAnnotation.continuous_eval_id == continuous_eval.id,
                *self._live_runs_since(window_start),
            )
            .one()
        )

        return ContinuousEvalSpendResponse(
            continuous_eval_id=continuous_eval.id,
            last_24h_run_count=row.day_run_count,
            last_24h_cost=float(row.day_cost),
            estimate=self._build_estimate(
                task_id=continuous_eval.task_id,
                sample_rate=continuous_eval.sample_rate,
                run_count=row.run_count,
                average_run_cost=row.average_run_cost,
                window_start=window_start,
                now=now,
            ),
        )

    def estimate_daily_spend_for_llm_eval(
        self,
        task_id: str,
        llm_eval_name: str,
        sample_rate: Optional[float],
        now: Optional[datetime] = None,
        trace_filter: Optional[List[ContinuousEvalTraceFilterCondition]] = None,
    ) -> ContinuousEvalDailySpendEstimate:
        """Estimate for a continuous eval not created yet, priced from the live
        runs of the task's existing continuous evals that use the same evaluator.
        With a trace filter, also scaled by the share of recent traces it matches."""
        now = now or datetime.now()
        window_start = now - timedelta(days=SPEND_ESTIMATE_WINDOW_DAYS)
        cost = func.coalesce(DatabaseAgenticAnnotation.cost, 0.0)

        row = (
            self.db_session.query(*self._average_run_cost_columns(cost))
            .join(
                DatabaseContinuousEval,
                DatabaseAgenticAnnotation.continuous_eval_id
                == DatabaseContinuousEval.id,
            )
            .filter(
                DatabaseContinuousEval.task_id == task_id,
                DatabaseContinuousEval.llm_eval_name == llm_eval_name,
                *self._live_runs_since(window_start),
            )
            .one()
        )

        estimate = self._build_estimate(
            task_id=task_id,
            sample_rate=sample_rate,
            run_count=row.run_count,
            average_run_cost=row.average_run_cost,
            window_start=window_start,
            now=now,
        )
        if not trace_filter:
            return estimate

        matched, checked = self._count_filter_matches(
            task_id,
            window_start,
            now,
            trace_filter,
        )
        share = matched / checked if checked else None
        estimate.filter_match_share = share
        estimate.filter_traces_checked = checked
        if estimate.estimated_daily_cost is not None and share is not None:
            estimate.estimated_daily_cost *= share
        return estimate

    def _count_filter_matches(
        self,
        task_id: str,
        window_start: datetime,
        now: datetime,
        trace_filter: List[ContinuousEvalTraceFilterCondition],
    ) -> tuple[int, int]:
        """How many of the task's latest traces in the window match the filter,
        out of how many checked (at most FILTER_SHARE_MAX_TRACES)."""
        trace_ids = [
            trace_id
            for (trace_id,) in self.db_session.query(DatabaseTraceMetadata.trace_id)
            .filter(*self._task_traces_in_window(task_id, window_start, now))
            .order_by(DatabaseTraceMetadata.start_time.desc())
            .limit(FILTER_SHARE_MAX_TRACES)
        ]
        if not trace_ids:
            return 0, 0

        spans_by_trace: dict[str, list[DatabaseSpan]] = {
            trace_id: [] for trace_id in trace_ids
        }
        for span in self.db_session.query(DatabaseSpan).filter(
            DatabaseSpan.trace_id.in_(trace_ids),
        ):
            spans_by_trace[span.trace_id].append(span)

        matched = sum(
            1
            for spans in spans_by_trace.values()
            if spans_match_filter(spans, trace_filter)
        )
        return matched, len(trace_ids)

    @staticmethod
    def _task_traces_in_window(
        task_id: str,
        window_start: datetime,
        now: datetime,
    ) -> list[Any]:
        # Agent experiment traces are left out because continuous evals skip them.
        return [
            DatabaseTraceMetadata.task_id == task_id,
            DatabaseTraceMetadata.start_time >= window_start,
            DatabaseTraceMetadata.start_time < now,
            or_(
                DatabaseTraceMetadata.session_id.is_(None),
                ~DatabaseTraceMetadata.session_id.startswith(
                    AGENT_EXPERIMENT_SESSION_PREFIX,
                ),
            ),
        ]

    @staticmethod
    def _live_runs_since(window_start: datetime) -> list[Any]:
        return [
            DatabaseAgenticAnnotation.annotation_type
            == AgenticAnnotationType.CONTINUOUS_EVAL.value,
            DatabaseAgenticAnnotation.test_run_id.is_(None),
            DatabaseAgenticAnnotation.created_at >= window_start,
        ]

    @staticmethod
    def _average_run_cost_columns(cost: Any) -> list[Any]:
        called_llm = DatabaseAgenticAnnotation.run_status.in_(
            _LLM_CALLING_RUN_STATUSES,
        )
        return [
            func.count(case((called_llm, 1))).label("run_count"),
            func.avg(case((called_llm, cost))).label("average_run_cost"),
        ]

    def _count_task_traces(
        self,
        task_id: str,
        window_start: datetime,
        now: datetime,
    ) -> int:
        # trace_metadata holds one row per trace and is indexed on
        # (task_id, start_time), so this is cheaper than counting root spans.
        return int(
            self.db_session.query(func.count(DatabaseTraceMetadata.trace_id))
            .filter(*self._task_traces_in_window(task_id, window_start, now))
            .scalar()
            or 0,
        )

    def _build_estimate(
        self,
        task_id: str,
        sample_rate: Optional[float],
        run_count: int,
        average_run_cost: Optional[float],
        window_start: datetime,
        now: datetime,
    ) -> ContinuousEvalDailySpendEstimate:
        trace_count = self._count_task_traces(task_id, window_start, now)
        traces_per_day = trace_count / SPEND_ESTIMATE_WINDOW_DAYS
        effective_sample_rate = 1.0 if sample_rate is None else sample_rate
        average = (
            float(average_run_cost)
            if run_count and average_run_cost is not None
            else None
        )

        estimated_daily_cost: Optional[float] = None
        unavailable_reason: Optional[SpendEstimateUnavailableReason] = None
        if trace_count == 0:
            unavailable_reason = SpendEstimateUnavailableReason.NO_TRACES
        elif average is None:
            unavailable_reason = SpendEstimateUnavailableReason.NO_RUNS
        else:
            estimated_daily_cost = traces_per_day * effective_sample_rate * average

        return ContinuousEvalDailySpendEstimate(
            window_days=SPEND_ESTIMATE_WINDOW_DAYS,
            trace_count=trace_count,
            traces_per_day=traces_per_day,
            sample_rate=effective_sample_rate,
            run_count=run_count,
            average_run_cost=average,
            estimated_daily_cost=estimated_daily_cost,
            unavailable_reason=unavailable_reason,
        )
