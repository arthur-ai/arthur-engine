from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseTraceMetadata
from schemas.enums import SpendEstimateUnavailableReason
from schemas.internal_schemas import ContinuousEval
from schemas.response_schemas import (
    ContinuousEvalDailySpendEstimate,
    ContinuousEvalSpendResponse,
)
from utils.constants import AGENT_EXPERIMENT_SESSION_PREFIX

SPEND_ESTIMATE_WINDOW_DAYS = 7

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

        spent_today = self.spent_today(continuous_eval.id, now)
        cap = continuous_eval.daily_cost_cap_usd
        return ContinuousEvalSpendResponse(
            continuous_eval_id=continuous_eval.id,
            last_24h_run_count=row.day_run_count,
            last_24h_cost=float(row.day_cost),
            spent_today=spent_today,
            daily_cost_cap_usd=cap,
            cap_reached=cap is not None and spent_today >= cap,
            estimate=self._build_estimate(
                task_id=continuous_eval.task_id,
                sample_rate=continuous_eval.sample_rate,
                run_count=row.run_count,
                average_run_cost=row.average_run_cost,
                window_start=window_start,
                now=now,
            ),
        )

    def spent_today(
        self,
        continuous_eval_id: UUID,
        now: Optional[datetime] = None,
    ) -> float:
        """Cost of the eval's live runs judged since midnight, which is what the
        daily cap counts. The worker sets updated_at when it records a run's cost,
        so a run queued before midnight and judged after counts toward today. Run
        timestamps come from the same clock (datetime.now), so "today" is the
        engine's day."""
        now = now or datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return float(
            self.db_session.query(
                func.coalesce(func.sum(DatabaseAgenticAnnotation.cost), 0.0),
            )
            .filter(
                DatabaseAgenticAnnotation.continuous_eval_id == continuous_eval_id,
                DatabaseAgenticAnnotation.annotation_type
                == AgenticAnnotationType.CONTINUOUS_EVAL.value,
                DatabaseAgenticAnnotation.test_run_id.is_(None),
                DatabaseAgenticAnnotation.cost.is_not(None),
                DatabaseAgenticAnnotation.updated_at >= midnight,
            )
            .scalar(),
        )

    def estimate_daily_spend_for_llm_eval(
        self,
        task_id: str,
        llm_eval_name: str,
        sample_rate: Optional[float],
        now: Optional[datetime] = None,
    ) -> ContinuousEvalDailySpendEstimate:
        """Estimate for a continuous eval not created yet, priced from the live
        runs of the task's existing continuous evals that use the same evaluator."""
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

        return self._build_estimate(
            task_id=task_id,
            sample_rate=sample_rate,
            run_count=row.run_count,
            average_run_cost=row.average_run_cost,
            window_start=window_start,
            now=now,
        )

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
        # Agent experiment traces are left out because continuous evals skip them.
        return int(
            self.db_session.query(func.count(DatabaseTraceMetadata.trace_id))
            .filter(
                DatabaseTraceMetadata.task_id == task_id,
                DatabaseTraceMetadata.start_time >= window_start,
                DatabaseTraceMetadata.start_time < now,
                or_(
                    DatabaseTraceMetadata.session_id.is_(None),
                    ~DatabaseTraceMetadata.session_id.startswith(
                        AGENT_EXPERIMENT_SESSION_PREFIX,
                    ),
                ),
            )
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
