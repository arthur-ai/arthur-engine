from datetime import datetime, timedelta
from typing import Any, Optional

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
# Runs that are done one way or another: called the LLM, or were skipped before
# it. Their split is the share of sampled traces that reach the judge. ERROR is
# left out of both sides: it covers failures before the judge (missing variables)
# and during it (quota, provider errors), so it says nothing about whether a
# sampled trace would reach the judge, and counting it would lower the estimate
# whenever the provider is failing.
_FINISHED_RUN_STATUSES = (
    *_LLM_CALLING_RUN_STATUSES,
    ContinuousEvalRunStatus.SKIPPED.value,
)
# continuous_evals.eval_type of evals that call an LLM judge ("ml_eval" otherwise).
_LLM_EVAL_TYPE = "llm_eval"


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
            )
            .filter(
                DatabaseAgenticAnnotation.continuous_eval_id == continuous_eval.id,
                *self._live_runs_since(window_start),
            )
            .one()
        )
        # Price only runs made by the current evaluator: a judge switch otherwise
        # mixes models for the whole window (measured: 29-37x too high for days
        # after switching GPT-5.5 to Haiku).
        priced_since = max(
            window_start, continuous_eval.judge_changed_at or window_start
        )
        priced = (
            self.db_session.query(*self._average_run_cost_columns())
            .join(
                DatabaseContinuousEval,
                DatabaseAgenticAnnotation.continuous_eval_id
                == DatabaseContinuousEval.id,
            )
            .filter(
                DatabaseAgenticAnnotation.continuous_eval_id == continuous_eval.id,
                # ML evals finish runs without calling the LLM, so they have no cost
                # to price and must not count as unpriced LLM calls.
                DatabaseContinuousEval.eval_type == _LLM_EVAL_TYPE,
                *self._live_runs_since(priced_since),
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
                priced=priced,
                priced_since=priced_since if priced_since > window_start else None,
                window_start=window_start,
                now=now,
            ),
        )

    def estimate_daily_spend_for_llm_eval(
        self,
        task_id: str,
        llm_eval_name: str,
        llm_eval_version: int,
        sample_rate: Optional[float],
        now: Optional[datetime] = None,
    ) -> ContinuousEvalDailySpendEstimate:
        """Estimate for a continuous eval not created yet, priced from the live
        runs of the task's existing continuous evals that use the same evaluator
        version (each version can use a different judge model)."""
        now = now or datetime.now()
        window_start = now - timedelta(days=SPEND_ESTIMATE_WINDOW_DAYS)

        priced = (
            self.db_session.query(*self._average_run_cost_columns())
            .join(
                DatabaseContinuousEval,
                DatabaseAgenticAnnotation.continuous_eval_id
                == DatabaseContinuousEval.id,
            )
            .filter(
                DatabaseContinuousEval.task_id == task_id,
                DatabaseContinuousEval.llm_eval_name == llm_eval_name,
                DatabaseContinuousEval.llm_eval_version == llm_eval_version,
                DatabaseContinuousEval.eval_type == _LLM_EVAL_TYPE,
                *self._live_runs_since(window_start),
                # Each eval's runs from its current evaluator only.
                or_(
                    DatabaseContinuousEval.judge_changed_at.is_(None),
                    DatabaseAgenticAnnotation.created_at
                    >= DatabaseContinuousEval.judge_changed_at,
                ),
            )
            .one()
        )

        return self._build_estimate(
            task_id=task_id,
            sample_rate=sample_rate,
            priced=priced,
            priced_since=None,
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
    def _average_run_cost_columns() -> list[Any]:
        cost = DatabaseAgenticAnnotation.cost
        called_llm = DatabaseAgenticAnnotation.run_status.in_(
            _LLM_CALLING_RUN_STATUSES,
        )
        priced = called_llm & cost.is_not(None)
        finished = DatabaseAgenticAnnotation.run_status.in_(_FINISHED_RUN_STATUSES)
        return [
            func.count(case((priced, 1))).label("run_count"),
            # A run without a cost (a model litellm has no price for) would pull the
            # average toward $0, so it is counted separately instead.
            func.avg(case((priced, cost))).label("average_run_cost"),
            func.count(case((called_llm & cost.is_(None), 1))).label(
                "unpriced_run_count",
            ),
            func.count(case((called_llm, 1))).label("judged_run_count"),
            func.count(case((finished, 1))).label("finished_run_count"),
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
        priced: Any,
        priced_since: Optional[datetime],
        window_start: datetime,
        now: datetime,
    ) -> ContinuousEvalDailySpendEstimate:
        trace_count = self._count_task_traces(task_id, window_start, now)
        traces_per_day = trace_count / SPEND_ESTIMATE_WINDOW_DAYS
        effective_sample_rate = 1.0 if sample_rate is None else sample_rate
        run_count = priced.run_count
        average = (
            float(priced.average_run_cost)
            if run_count and priced.average_run_cost is not None
            else None
        )
        # Sampled traces that are skipped (a missing span) cost nothing, so only the
        # share that reaches the judge is priced.
        judged_share = (
            priced.judged_run_count / priced.finished_run_count
            if priced.finished_run_count
            else 1.0
        )

        estimated_daily_cost: Optional[float] = None
        unavailable_reason: Optional[SpendEstimateUnavailableReason] = None
        if trace_count == 0:
            unavailable_reason = SpendEstimateUnavailableReason.NO_TRACES
        elif average is None:
            unavailable_reason = SpendEstimateUnavailableReason.NO_RUNS
        else:
            estimated_daily_cost = (
                traces_per_day * effective_sample_rate * judged_share * average
            )

        return ContinuousEvalDailySpendEstimate(
            window_days=SPEND_ESTIMATE_WINDOW_DAYS,
            trace_count=trace_count,
            traces_per_day=traces_per_day,
            sample_rate=effective_sample_rate,
            run_count=run_count,
            average_run_cost=average,
            judged_share=judged_share,
            unpriced_run_count=priced.unpriced_run_count,
            priced_since=priced_since,
            estimated_daily_cost=estimated_daily_cost,
            unavailable_reason=unavailable_reason,
        )
