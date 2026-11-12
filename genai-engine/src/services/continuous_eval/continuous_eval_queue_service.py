import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from clients.llm.llm_client import COST_UNAVAILABLE
from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.continuous_eval_test_run_models import DatabaseContinuousEvalTestRun
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseSpan
from dependencies import get_db_session
from repositories.continuous_eval_spend_repository import ContinuousEvalSpendRepository
from repositories.evaluator_factory import get_evaluator
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.organizations_repository import (
    enforce_token_quota,
    extract_token_limit_message,
)
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.common_schemas import ContinuousEvalTraceFilterCondition
from schemas.enums import (
    ContinuousEvalRollupRule,
    ContinuousEvalRunLevel,
    EvalKind,
    TestRunStatus,
)
from schemas.internal_schemas import ContinuousEval
from schemas.response_schemas import TransformExtractionResponseList
from schemas.transform_schemas import TraceTransformDefinition
from services.base_queue_service import BaseQueueJob, BaseQueueService
from services.continuous_eval.span_scope import (
    SPAN_SCOPE_IDLE_SECONDS,
    SPAN_SCOPE_MAX_WAIT_SECONDS,
    SpanVerdict,
    cap_checked_before_each_span_run,
    decide_rollup,
)
from utils.span_selection import select_spans
from utils.span_tree import tree_order
from utils.stored_value import cap_stored_value
from utils.trace import validate_span_version
from utils.transform_executor import (
    execute_transform_on_spans,
    spans_match_filter,
)

logger = logging.getLogger(__name__)

# Statuses of runs that made, or are about to make, an LLM call
_LLM_CALL_RUN_STATUSES = (
    ContinuousEvalRunStatus.PENDING.value,
    ContinuousEvalRunStatus.RUNNING.value,
    ContinuousEvalRunStatus.PASSED.value,
    ContinuousEvalRunStatus.FAILED.value,
)

# Start of the run description for a trace the eval's trace filter left out
TRACE_FILTER_SKIP_DESCRIPTION = "Trace did not match the trace filter"

# A prompt cache write costs 1.25x the uncached input price and lasts 5 minutes, so
# a continuous eval only gets a cache breakpoint once it runs often enough to read
# the cache back before it expires
CACHE_BREAKPOINT_WINDOW = timedelta(minutes=5)
CACHE_BREAKPOINT_MIN_RECENT_RUNS = 2


def runs_often_enough_to_cache(
    db_session: Session,
    continuous_eval_id: uuid.UUID,
) -> bool:
    """Whether the continuous eval has had enough runs created within the cache
    lifetime, test runs included, for a cache write to be read back. Skipped and
    errored runs made no LLM call, so they don't count.

    Range-scans the (continuous_eval_id, created_at) index and stops at
    CACHE_BREAKPOINT_MIN_RECENT_RUNS matching rows, so busy evals stay cheap to
    check."""
    recent_runs = (
        db_session.query(DatabaseAgenticAnnotation.continuous_eval_id)
        .filter(
            DatabaseAgenticAnnotation.continuous_eval_id == continuous_eval_id,
            DatabaseAgenticAnnotation.created_at
            >= datetime.now() - CACHE_BREAKPOINT_WINDOW,
            DatabaseAgenticAnnotation.run_status.in_(_LLM_CALL_RUN_STATUSES),
            # A rollup never calls the judge.
            DatabaseAgenticAnnotation.run_level
            != ContinuousEvalRunLevel.SPAN_ROLLUP.value,
        )
        .limit(CACHE_BREAKPOINT_MIN_RECENT_RUNS)
        .count()
    )
    return recent_runs >= CACHE_BREAKPOINT_MIN_RECENT_RUNS


class RunAlreadyClaimed(Exception):
    """The run is no longer pending: another worker has claimed or finished it,
    so this job leaves it alone."""


class ContinuousEvalJob(BaseQueueJob):
    """Represents a continuous eval job to be executed."""

    def __init__(
        self,
        annotation_id: uuid.UUID,
        trace_id: str,
        continuous_eval_id: uuid.UUID,
        task_id: str,
        delay_seconds: int = 10,
    ):
        super().__init__(delay_seconds)
        self.annotation_id = annotation_id
        self.trace_id = trace_id
        self.continuous_eval_id = continuous_eval_id
        self.task_id = task_id


class ContinuousEvalQueueService(BaseQueueService[ContinuousEvalJob]):
    """Service that manages async execution of continuous evals using ThreadPoolExecutor."""

    job_model = ContinuousEvalJob
    service_name = "continuous_eval_queue_service"
    background_thread_name = "continuous-eval-background"

    def _get_job_key(self, job: ContinuousEvalJob) -> uuid.UUID:
        """Use annotation_id as the unique key for deduplication."""
        return job.annotation_id

    def _background_loop(self) -> None:
        """Background thread that checks for stale pending annotations and re-queues them."""
        logger.info(f"Background thread started for {self.service_name}")

        while not self.shutdown_event.is_set():
            try:
                # Wait for 1 hour or until shutdown
                if self.shutdown_event.wait(timeout=3600):
                    break

                # Find pending annotations older than 15 minutes that haven't been executed
                self._check_stale_annotations()

            except Exception as e:
                logger.error(f"Error in background loop: {e}", exc_info=True)

        logger.info("Background thread stopped")

    def _check_stale_annotations(self) -> None:
        """Find and re-queue pending annotations that are older than 15 minutes."""
        db_session = next(get_db_session())
        try:
            cutoff_time = datetime.now() - timedelta(minutes=15)

            stale_annotations = (
                db_session.query(DatabaseAgenticAnnotation, DatabaseContinuousEval)
                .join(
                    DatabaseContinuousEval,
                    DatabaseAgenticAnnotation.continuous_eval_id
                    == DatabaseContinuousEval.id,
                )
                .filter(
                    DatabaseAgenticAnnotation.annotation_type
                    == AgenticAnnotationType.CONTINUOUS_EVAL.value,
                    DatabaseAgenticAnnotation.run_status
                    == ContinuousEvalRunStatus.PENDING.value,
                    DatabaseAgenticAnnotation.created_at < cutoff_time,
                )
                .all()
            )

            if not stale_annotations:
                logger.debug("No stale annotations found")
                return

            logger.info(
                f"Found {len(stale_annotations)} stale pending annotations, re-queueing",
            )

            enqueued_count = 0
            for annotation, continuous_eval in stale_annotations:
                job = ContinuousEvalJob(
                    annotation_id=annotation.id,
                    trace_id=annotation.trace_id,
                    continuous_eval_id=annotation.continuous_eval_id,
                    task_id=continuous_eval.task_id,
                    delay_seconds=0,
                )
                enqueued, _ = self.enqueue(job)
                if enqueued:
                    enqueued_count += 1

            if enqueued_count > 0:
                info_message = f"Re-queued {enqueued_count} stale annotations"
                info_message += (
                    f" ({len(stale_annotations) - enqueued_count} already active)"
                    if len(stale_annotations) - enqueued_count > 0
                    else ""
                )
                logger.info(info_message)

        except Exception as e:
            logger.error(f"Error checking stale annotations: {e}", exc_info=True)
        finally:
            db_session.close()

    def _execute_job(self, job: ContinuousEvalJob) -> None:
        """Execute a single evaluation job.

        A trace-scope run (run_level 'trace') judges the trace. In span scope the
        trace's rollup job fans out to one span run per matching span, each span
        run judges its span, and the last one to finish sets the rollup.
        """
        db_session = next(get_db_session())
        run_level: Optional[str] = None
        try:
            annotation = self._load_pending_run(db_session, job)
            run_level = annotation.run_level

            # UP-4390: short-circuit if the owning org is out of LLM credits.
            # The upstream trace may have spans missing because the agent's
            # own LLM calls were 429'd, and the eval itself would 429 too.
            # Surface the credit-limit message instead of leaving the user
            # to interpret a downstream "missing variables" or "unexpected
            # error" symptom.
            try:
                enforce_token_quota(annotation.org_id)
            except HTTPException as exc:
                self._update_annotation_status(
                    db_session,
                    job.annotation_id,
                    ContinuousEvalRunStatus.ERROR.value,
                    annotation_description=extract_token_limit_message(exc) or str(exc),
                )
                if run_level == ContinuousEvalRunLevel.SPAN.value:
                    self._finish_rollups_if_done(db_session, annotation)
                return

            # Load the continuous eval configuration
            db_continuous_eval = (
                db_session.query(DatabaseContinuousEval)
                .filter(DatabaseContinuousEval.id == job.continuous_eval_id)
                .first()
            )

            if not db_continuous_eval:
                raise ValueError(f"Continuous eval {job.continuous_eval_id} not found")

            if run_level == ContinuousEvalRunLevel.SPAN_ROLLUP.value:
                self._fan_out(db_session, job, annotation, db_continuous_eval)
            elif run_level == ContinuousEvalRunLevel.SPAN.value:
                self._judge_span(db_session, job, annotation, db_continuous_eval)
            else:
                self._judge_trace(db_session, job, annotation, db_continuous_eval)

        except RunAlreadyClaimed as e:
            # A duplicate job (a stale-run re-queue, another node) found the run
            # taken: writing ERROR here would clobber the claiming worker's result
            # and could finish a span-scope rollup early.
            logger.info(str(e))
        except Exception as e:
            logger.error(
                f"Error executing job for trace {job.trace_id}: {e}",
                exc_info=True,
            )
            # Catch the gate firing mid-eval (e.g. the org crossed the limit
            # between the pre-check and the eval's LLM call) and surface the
            # structured credit-limit message instead of HTTPException(...)
            # stringified verbatim.
            description = extract_token_limit_message(e) or str(e)
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.ERROR.value,
                annotation_description=description,
            )
            if run_level == ContinuousEvalRunLevel.SPAN.value:
                db_annotation = db_session.get(
                    DatabaseAgenticAnnotation,
                    job.annotation_id,
                )
                if db_annotation is not None:
                    self._finish_rollups_if_done(db_session, db_annotation)
            raise e
        finally:
            db_session.close()

    def _load_pending_run(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
    ) -> DatabaseAgenticAnnotation:
        annotation = (
            db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.id == job.annotation_id)
            .first()
        )

        if not annotation:
            raise ValueError(f"Annotation {job.annotation_id} not found")
        if annotation.annotation_type != AgenticAnnotationType.CONTINUOUS_EVAL.value:
            raise ValueError(
                f"Annotation {job.annotation_id} is not a continuous eval",
            )
        if annotation.trace_id != job.trace_id:
            raise ValueError(
                f"Annotation's trace ID does not match the job's trace ID",
            )
        if annotation.continuous_eval_id != job.continuous_eval_id:
            raise ValueError(
                f"Annotation's continuous eval ID does not match the job's continuous eval ID",
            )
        if annotation.run_status != ContinuousEvalRunStatus.PENDING.value:
            raise RunAlreadyClaimed(
                f"Annotation {job.annotation_id} is running or has already finished executing",
            )
        return annotation

    def _transform_definition(
        self,
        db_session: Session,
        db_continuous_eval: DatabaseContinuousEval,
    ) -> TraceTransformDefinition:
        # Verify the transform exists
        trace_transform_repository = TraceTransformRepository(db_session)
        trace_transform = trace_transform_repository.get_transform_by_id(
            db_continuous_eval.transform_id,
        )
        if not trace_transform:
            raise ValueError(
                f"Transform {db_continuous_eval.transform_id} not found",
            )

        # Use pinned version's definition if set, otherwise use the latest version
        if db_continuous_eval.transform_version_id is not None:
            pinned_version = trace_transform_repository.get_version_by_id(
                db_continuous_eval.transform_id,
                db_continuous_eval.transform_version_id,
            )
            return pinned_version.definition
        return trace_transform_repository.get_latest_definition(
            db_continuous_eval.transform_id,
        )

    @staticmethod
    def _load_spans(db_session: Session, trace_id: str) -> list[DatabaseSpan]:
        """The trace's spans as a flat list, straight from the spans table, the
        same spans get_trace_by_id serves (current span version only). A span id
        stored twice (re-sent by an exporter) keeps its first row, so fan-out and
        'current' reads see one span per id."""
        spans: dict[str, DatabaseSpan] = {}
        for span in (
            db_session.query(DatabaseSpan)
            .filter(
                DatabaseSpan.trace_id == trace_id,
            )
            .order_by(DatabaseSpan.created_at, DatabaseSpan.id)
        ):
            if span.span_id not in spans and validate_span_version(span.raw_data):
                spans[span.span_id] = span
        return list(spans.values())

    def _judge_trace(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
        annotation: DatabaseAgenticAnnotation,
        db_continuous_eval: DatabaseContinuousEval,
    ) -> None:
        # The flat span list, as span scope reads it, rather than the trace tree:
        # the tree builder drops spans caught in a parent cycle, and tree_order
        # (inside the transform) promotes them to roots instead.
        spans = self._load_spans(db_session, job.trace_id)
        if not spans:
            raise ValueError(f"Trace {job.trace_id} not found")
        judged_span_count = len(spans)

        # Checked here rather than at enqueue: the worker sees the whole trace,
        # so conditions on child spans (a model name, a tool's output) work too.
        if db_continuous_eval.trace_filter and not spans_match_filter(
            spans,
            [
                ContinuousEvalTraceFilterCondition.model_validate(condition)
                for condition in db_continuous_eval.trace_filter
            ],
        ):
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=(
                    f"{TRACE_FILTER_SKIP_DESCRIPTION} for eval {job.continuous_eval_id}"
                ),
                judged_span_count=judged_span_count,
            )
            return

        transform_definition = self._transform_definition(
            db_session,
            db_continuous_eval,
        )

        # Execute the transform over the trace
        transform_results = execute_transform_on_spans(spans, transform_definition)
        self._judge_and_store(
            db_session,
            job,
            annotation,
            db_continuous_eval,
            transform_results,
            judged_span_count=judged_span_count,
            check_cap=True,
        )

    def _judge_span(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
        annotation: DatabaseAgenticAnnotation,
        db_continuous_eval: DatabaseContinuousEval,
    ) -> None:
        """One span run: the transform reads the trace with this span as the
        'current' one, and the judge is called once for it."""
        spans = self._load_spans(db_session, job.trace_id)
        if annotation.span_id not in {span.span_id for span in spans}:
            raise ValueError(
                f"Span {annotation.span_id} not found in trace {job.trace_id}",
            )
        transform_results = execute_transform_on_spans(
            spans,
            self._transform_definition(db_session, db_continuous_eval),
            current_span_id=annotation.span_id,
        )
        self._judge_and_store(
            db_session,
            job,
            annotation,
            db_continuous_eval,
            transform_results,
            judged_span_count=len(spans),
            check_cap=cap_checked_before_each_span_run(),
        )
        self._finish_rollups_if_done(db_session, annotation)

    def _judge_and_store(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
        annotation: DatabaseAgenticAnnotation,
        db_continuous_eval: DatabaseContinuousEval,
        transform_results: TransformExtractionResponseList,
        judged_span_count: int,
        check_cap: bool,
    ) -> None:
        """Map the transform's variables to the eval's, call the judge once and
        store the verdict on the run. Skips or errors the run instead when the
        variables are incomplete, the mapping is off, or the daily cap is spent."""
        if len(transform_results.missing_spans) > 0:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=f"Spans {', '.join(transform_results.missing_spans)} not found in trace {job.trace_id} skipping continuous eval execution for eval {job.continuous_eval_id}",
                judged_span_count=judged_span_count,
            )
            return
        if len(transform_results.missing_variables) > 0:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.ERROR.value,
                annotation_description=f"Could not extract variables: {', '.join(transform_results.missing_variables)} using transform {db_continuous_eval.transform_id} on trace {job.trace_id}",
                judged_span_count=judged_span_count,
            )
            return

        # Get the mapping from transform var to eval var
        continuous_eval = ContinuousEval.from_db_model(db_continuous_eval)
        mapping_dict: dict[str, str] = {}
        for mapping in continuous_eval.transform_variable_mapping:
            mapping_dict[mapping.transform_variable] = mapping.eval_variable

        # Resolve transform variables into eval variable names
        resolved_variables: dict[str, str] = {}
        for variable in transform_results.variables:
            if variable.name in mapping_dict:
                resolved_variables[mapping_dict[variable.name]] = variable.value

        eval_name = continuous_eval.llm_eval_name
        eval_version = str(continuous_eval.llm_eval_version)

        if eval_name is None or continuous_eval.llm_eval_version is None:
            raise ValueError(
                f"Continuous eval {continuous_eval.id} has no eval configured.",
            )

        # Look up the eval via the repository to get its eval_type for dispatching.
        llm_eval = LLMEvalsRepository(db_session).get_llm_item(
            continuous_eval.task_id,
            eval_name,
            eval_version,
        )
        eval_type = EvalKind(llm_eval.eval_kind)
        evaluator = get_evaluator(db_session, eval_type)

        # Validate that the resolved eval vars match what the evaluator expects
        expected_vars = set(
            evaluator.get_eval_variables(
                continuous_eval.task_id,
                eval_name,
                eval_version,
            ),
        )
        mapped_eval_vars = set(resolved_variables.keys())
        if mapped_eval_vars != expected_vars:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=f"Mapped eval variables: {', '.join(mapped_eval_vars)} do not match eval variables: {', '.join(expected_vars)}",
                judged_span_count=judged_span_count,
            )
            return

        # Checked right before the judge call rather than when the run is queued:
        # a burst queues every trace before any of their costs exist, so only a
        # check here sees the spend of the runs that went before it. Runs already
        # calling the judge can still finish past the cap: at most one per worker
        # thread, in every engine process.
        # Test runs are started by hand and don't count toward the cap, so they
        # aren't held back by it either.
        if check_cap and self._skip_if_cap_reached(
            db_session,
            job,
            annotation,
            db_continuous_eval,
        ):
            return

        # Update annotation status to running
        # NOTE: We are not using _update_annotation_status here so we can atomically update the status from pending to running
        # and ensure only one worker across all nodes can execute this job
        updated_rows = (
            db_session.query(DatabaseAgenticAnnotation)
            .filter(
                DatabaseAgenticAnnotation.id == job.annotation_id,
                DatabaseAgenticAnnotation.run_status
                == ContinuousEvalRunStatus.PENDING.value,
            )
            .update(
                {
                    "run_status": ContinuousEvalRunStatus.RUNNING.value,
                    "updated_at": datetime.now(),
                },
                synchronize_session=False,
            )
        )
        db_session.commit()

        if updated_rows == 0:
            logger.info(
                f"Annotation {job.annotation_id} was already picked up by another worker, skipping",
            )
            return

        db_session.expire_all()

        # annotation.org_id is denormalized at enqueue time so the
        # background worker doesn't need to chase task → org each call.
        eval_run_result = evaluator.run(
            task_id=continuous_eval.task_id,
            eval_name=eval_name,
            eval_version=eval_version,
            variable_mapping=continuous_eval.transform_variable_mapping,
            resolved_variables=resolved_variables,
            org_id=annotation.org_id,
            add_cache_breakpoint=(
                eval_type == EvalKind.LLM_AS_A_JUDGE
                and runs_often_enough_to_cache(db_session, job.continuous_eval_id)
            ),
        )
        run_status = (
            ContinuousEvalRunStatus.PASSED.value
            if eval_run_result.score
            else ContinuousEvalRunStatus.FAILED.value
        )
        input_variables = [
            VariableTemplateValue(name=k, value=cap_stored_value(v))
            for k, v in resolved_variables.items()
        ]
        self._update_annotation_status(
            db_session,
            job.annotation_id,
            run_status,
            input_variables=input_variables,
            annotation_score=int(eval_run_result.score),
            annotation_description=eval_run_result.reason,
            label=eval_run_result.label,
            cost=(
                float(eval_run_result.cost)
                if eval_run_result.cost and eval_run_result.cost != COST_UNAVAILABLE
                else None
            ),
            judged_span_count=judged_span_count,
        )

    def _skip_if_cap_reached(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
        annotation: DatabaseAgenticAnnotation,
        db_continuous_eval: DatabaseContinuousEval,
    ) -> bool:
        cap = db_continuous_eval.daily_cost_cap_usd
        if (
            cap is None
            or annotation.test_run_id is not None
            or ContinuousEvalSpendRepository(db_session).spent_today(
                db_continuous_eval.id,
            )
            < cap
        ):
            return False
        logger.info(
            f"Skipping run {job.annotation_id}: continuous eval "
            f"{db_continuous_eval.id} reached its daily spend cap of ${cap:g}",
        )
        # Only a still-pending run is skipped, so a worker that has already
        # claimed this run keeps its result.
        db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.id == job.annotation_id,
            DatabaseAgenticAnnotation.run_status
            == ContinuousEvalRunStatus.PENDING.value,
        ).update(
            {
                "run_status": ContinuousEvalRunStatus.SKIPPED.value,
                "annotation_description": (
                    f"Daily spend cap of ${cap:g} reached; runs resume at midnight "
                    "(engine clock, UTC by default)."
                ),
                "updated_at": datetime.now(),
            },
            synchronize_session=False,
        )
        db_session.commit()
        if annotation.run_level == ContinuousEvalRunLevel.SPAN.value:
            self._finish_rollups_if_done(db_session, annotation)
        return True

    def _fan_out(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
        rollup: DatabaseAgenticAnnotation,
        db_continuous_eval: DatabaseContinuousEval,
    ) -> None:
        """A span-scope trace's rollup job: once the trace is idle, create one span
        run per matching span (up to max_spans_per_trace) and queue them."""
        spans = self._load_spans(db_session, job.trace_id)
        if not spans:
            raise ValueError(f"Trace {job.trace_id} not found")

        # Wait for the trace to go quiet, so late spans (a retried tool call, the
        # final answer) are judged too, but never past the maximum wait. A test run
        # picks finished traces by hand, so it doesn't wait.
        quiet_for = self._seconds_since_last_span(db_session, job.trace_id)
        if (
            rollup.test_run_id is None
            and quiet_for < SPAN_SCOPE_IDLE_SECONDS
            and datetime.now() - rollup.created_at
            < timedelta(seconds=SPAN_SCOPE_MAX_WAIT_SECONDS)
        ):
            job.requeue_in = SPAN_SCOPE_IDLE_SECONDS - quiet_for
            logger.debug(
                f"Trace {job.trace_id} is still receiving spans; fanning out "
                f"eval {job.continuous_eval_id} in {job.requeue_in:.0f}s",
            )
            return

        judged_span_count = len(spans)
        if db_continuous_eval.trace_filter and not spans_match_filter(
            spans,
            [
                ContinuousEvalTraceFilterCondition.model_validate(condition)
                for condition in db_continuous_eval.trace_filter
            ],
        ):
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=(
                    f"{TRACE_FILTER_SKIP_DESCRIPTION} for eval {job.continuous_eval_id}"
                ),
                judged_span_count=judged_span_count,
            )
            return

        # The cap is checked once per trace, here: see SPAN_SCOPE_CAP_CHECK_AT.
        if self._skip_if_cap_reached(db_session, job, rollup, db_continuous_eval):
            # Span runs a rerun reopened are not judged either.
            self._span_run_query(
                db_session,
                rollup,
                ContinuousEvalRunLevel.SPAN,
            ).filter(
                DatabaseAgenticAnnotation.run_status
                == ContinuousEvalRunStatus.PENDING.value,
            ).update(
                {
                    "run_status": ContinuousEvalRunStatus.SKIPPED.value,
                    "annotation_description": "Skipped with its trace: daily spend cap reached",
                    "updated_at": datetime.now(),
                },
                synchronize_session=False,
            )
            db_session.commit()
            return

        continuous_eval = ContinuousEval.from_db_model(db_continuous_eval)
        if continuous_eval.span_filter is None:
            raise ValueError(
                f"Continuous eval {continuous_eval.id} is span scope without a span filter",
            )
        candidates = select_spans(tree_order(spans), continuous_eval.span_filter)
        if not candidates:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=(
                    f"No span in trace {job.trace_id} matched the span filter of "
                    f"eval {job.continuous_eval_id}"
                ),
                judged_span_count=judged_span_count,
            )
            return
        judged = candidates[: continuous_eval.max_spans_per_trace]
        span_runs = self._ensure_span_runs(db_session, rollup, judged)

        claimed = (
            db_session.query(DatabaseAgenticAnnotation)
            .filter(
                DatabaseAgenticAnnotation.id == rollup.id,
                DatabaseAgenticAnnotation.run_status
                == ContinuousEvalRunStatus.PENDING.value,
            )
            .update(
                {
                    "run_status": ContinuousEvalRunStatus.RUNNING.value,
                    "annotation_description": (
                        f"Judging {len(judged)} of {len(candidates)} matching spans"
                    ),
                    "judged_span_count": judged_span_count,
                    "updated_at": datetime.now(),
                },
                synchronize_session=False,
            )
        )
        db_session.commit()
        if claimed == 0:
            logger.info(f"Rollup {rollup.id} was already fanned out, skipping")
            return

        for span_run in span_runs:
            if span_run.run_status == ContinuousEvalRunStatus.PENDING.value:
                self.enqueue(
                    ContinuousEvalJob(
                        annotation_id=span_run.id,
                        trace_id=job.trace_id,
                        continuous_eval_id=job.continuous_eval_id,
                        task_id=job.task_id,
                        delay_seconds=0,
                    ),
                )
        # A retried fan-out may find every span run already finished.
        self._finish_rollups_if_done(db_session, rollup)

    @staticmethod
    def _seconds_since_last_span(db_session: Session, trace_id: str) -> float:
        """How long the trace has gone without a new span. Spans get created_at
        from the database clock, so it is compared with that clock, not the
        engine's: the two can differ by a time zone."""
        last_span_at, db_now = (
            db_session.query(
                func.max(DatabaseSpan.created_at),
                func.current_timestamp(),
            )
            .filter(DatabaseSpan.trace_id == trace_id)
            .one()
        )
        if last_span_at is None:
            return float("inf")
        if isinstance(db_now, str):
            db_now = datetime.fromisoformat(db_now)
        if isinstance(last_span_at, str):
            last_span_at = datetime.fromisoformat(last_span_at)
        quiet: float = (db_now.replace(tzinfo=None) - last_span_at).total_seconds()
        return max(0.0, quiet)

    def _span_run_query(
        self,
        db_session: Session,
        run: DatabaseAgenticAnnotation,
        run_level: ContinuousEvalRunLevel,
    ) -> Any:
        """Runs of one level for the same eval, trace and test run as run."""
        test_run_match = (
            DatabaseAgenticAnnotation.test_run_id.is_(None)
            if run.test_run_id is None
            else DatabaseAgenticAnnotation.test_run_id == run.test_run_id
        )
        return db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.continuous_eval_id == run.continuous_eval_id,
            DatabaseAgenticAnnotation.trace_id == run.trace_id,
            DatabaseAgenticAnnotation.run_level == run_level.value,
            test_run_match,
        )

    def _ensure_span_runs(
        self,
        db_session: Session,
        rollup: DatabaseAgenticAnnotation,
        spans: list[DatabaseSpan],
    ) -> list[DatabaseAgenticAnnotation]:
        """One span run per span, reusing any a previous attempt made. The unique
        span-run indexes make a concurrent fan-out lose cleanly."""
        existing = {
            run.span_id
            for run in self._span_run_query(
                db_session,
                rollup,
                ContinuousEvalRunLevel.SPAN,
            )
        }
        now = datetime.now()
        for span in spans:
            if span.span_id in existing:
                continue
            db_session.add(
                DatabaseAgenticAnnotation(
                    id=uuid.uuid4(),
                    annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL.value,
                    trace_id=rollup.trace_id,
                    span_id=span.span_id,
                    continuous_eval_id=rollup.continuous_eval_id,
                    run_status=ContinuousEvalRunStatus.PENDING.value,
                    run_level=ContinuousEvalRunLevel.SPAN.value,
                    test_run_id=rollup.test_run_id,
                    created_at=now,
                    updated_at=now,
                    org_id=rollup.org_id,
                ),
            )
        try:
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
            logger.info(
                f"Span runs for trace {rollup.trace_id} were created by another "
                "worker; using those",
            )
        wanted = {span.span_id for span in spans}
        return [
            run
            for run in self._span_run_query(
                db_session,
                rollup,
                ContinuousEvalRunLevel.SPAN,
            )
            if run.span_id in wanted
        ]

    def _finish_rollups_if_done(
        self,
        db_session: Session,
        run: DatabaseAgenticAnnotation,
    ) -> None:
        """Once no span run of the trace is pending or running, give its rollup
        the verdict the eval's rollup rule takes from them."""
        db_session.expire_all()
        rollups = [
            rollup
            for rollup in self._span_run_query(
                db_session,
                run,
                ContinuousEvalRunLevel.SPAN_ROLLUP,
            )
            if rollup.run_status == ContinuousEvalRunStatus.RUNNING.value
        ]
        if not rollups:
            return
        db_continuous_eval = db_session.get(
            DatabaseContinuousEval,
            run.continuous_eval_id,
        )
        if db_continuous_eval is None:
            return
        continuous_eval = ContinuousEval.from_db_model(db_continuous_eval)
        span_runs = list(
            self._span_run_query(db_session, run, ContinuousEvalRunLevel.SPAN),
        )
        spans = self._load_spans(db_session, run.trace_id or "")
        ordered = tree_order(spans)
        position = {span.span_id: i for i, span in enumerate(ordered)}
        by_id = {span.span_id: span for span in spans}
        span_runs.sort(key=lambda r: position.get(r.span_id or "", len(position)))
        verdicts = [
            SpanVerdict(
                span_id=span_run.span_id or "",
                parent_span_id=(
                    by_id[span_run.span_id].parent_span_id
                    if span_run.span_id in by_id
                    else None
                ),
                span_name=(
                    by_id[span_run.span_id].span_name
                    if span_run.span_id in by_id
                    else None
                ),
                status=ContinuousEvalRunStatus(span_run.run_status),
                label=span_run.label,
            )
            for span_run in span_runs
        ]
        not_judged = 0
        if continuous_eval.span_filter is not None:
            not_judged = max(
                0,
                len(select_spans(ordered, continuous_eval.span_filter))
                - len(span_runs),
            )
        decision = decide_rollup(
            verdicts,
            continuous_eval.rollup_rule or ContinuousEvalRollupRule.ANY_FAIL,
            not_judged=not_judged,
        )
        if decision is None:
            return
        for rollup in rollups:
            # Only the worker that moves the rollup off RUNNING records it, so a
            # test run counts each trace once.
            finished = (
                db_session.query(DatabaseAgenticAnnotation)
                .filter(
                    DatabaseAgenticAnnotation.id == rollup.id,
                    DatabaseAgenticAnnotation.run_status
                    == ContinuousEvalRunStatus.RUNNING.value,
                )
                .update(
                    {
                        "run_status": decision.status.value,
                        "annotation_score": decision.score,
                        "annotation_description": decision.description,
                        "label": decision.label,
                        "updated_at": datetime.now(),
                    },
                    synchronize_session=False,
                )
            )
            db_session.commit()
            if finished and rollup.test_run_id:
                self._increment_test_run_counters(
                    db_session,
                    rollup.test_run_id,
                    decision.status.value,
                )

    def _update_annotation_status(
        self,
        db_session: Session,
        annotation_id: uuid.UUID,
        run_status: str,
        annotation_score: Optional[int] = None,
        annotation_description: Optional[str] = None,
        label: Optional[str] = None,
        input_variables: Optional[list[VariableTemplateValue]] = None,
        cost: Optional[float] = None,
        judged_span_count: Optional[int] = None,
    ) -> None:
        """Update annotation with execution results."""
        db_annotation = (
            db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.id == annotation_id)
            .first()
        )

        if not db_annotation:
            logger.error(f"Annotation {annotation_id} not found")
            return

        db_annotation.run_status = run_status
        db_annotation.updated_at = datetime.now()

        if annotation_score is not None:
            db_annotation.annotation_score = annotation_score
        if annotation_description is not None:
            db_annotation.annotation_description = annotation_description
        if label is not None:
            db_annotation.label = label
        if input_variables is not None:
            db_annotation.input_variables = [
                variable.model_dump() for variable in input_variables
            ]
        if judged_span_count is not None:
            db_annotation.judged_span_count = judged_span_count
        if cost is not None:
            # Added rather than replaced, so a rerun's judge call counts on top of
            # the earlier ones. Only the worker that claimed the run gets here.
            db_annotation.cost = (db_annotation.cost or 0.0) + cost

        db_session.commit()
        logger.debug(f"Updated annotation {annotation_id} to status {run_status}")

        # If this annotation belongs to a test run, update the test run counters.
        # A test run counts traces, so span runs count through their rollup.
        if (
            db_annotation.test_run_id
            and db_annotation.run_level != ContinuousEvalRunLevel.SPAN.value
        ):
            self._increment_test_run_counters(
                db_session,
                db_annotation.test_run_id,
                run_status,
            )

    def _increment_test_run_counters(
        self,
        db_session: Session,
        test_run_id: uuid.UUID,
        run_status: str,
    ) -> None:
        """Increment test run counters after an annotation completes.

        Uses two steps:
        1. Atomic SQL increment + commit (no read needed, safe under concurrency)
        2. Row-locked read to check completion and set final status
        """
        try:
            # Step 1: Atomically increment counters via SQL arithmetic
            update_values: dict[Any, Any] = {
                "completed_count": DatabaseContinuousEvalTestRun.completed_count + 1,
                "updated_at": datetime.now(),
            }

            if run_status == ContinuousEvalRunStatus.PASSED.value:
                update_values["passed_count"] = (
                    DatabaseContinuousEvalTestRun.passed_count + 1
                )
            elif run_status == ContinuousEvalRunStatus.FAILED.value:
                update_values["failed_count"] = (
                    DatabaseContinuousEvalTestRun.failed_count + 1
                )
            elif run_status == ContinuousEvalRunStatus.ERROR.value:
                update_values["error_count"] = (
                    DatabaseContinuousEvalTestRun.error_count + 1
                )
            elif run_status == ContinuousEvalRunStatus.SKIPPED.value:
                update_values["skipped_count"] = (
                    DatabaseContinuousEvalTestRun.skipped_count + 1
                )

            db_session.query(DatabaseContinuousEvalTestRun).filter(
                DatabaseContinuousEvalTestRun.id == test_run_id,
            ).update(update_values, synchronize_session=False)
            db_session.commit()

            # Step 2: Lock and check if all annotations are done
            # FOR UPDATE serializes concurrent completion checks and prevents
            # races with rerun decrements
            db_test_run = (
                db_session.query(DatabaseContinuousEvalTestRun)
                .filter(DatabaseContinuousEvalTestRun.id == test_run_id)
                .with_for_update()
                .first()
            )
            if db_test_run and db_test_run.completed_count >= db_test_run.total_count:
                all_errored = (
                    db_test_run.error_count + db_test_run.skipped_count
                    == db_test_run.total_count
                )
                has_issues = (
                    db_test_run.error_count > 0 or db_test_run.skipped_count > 0
                )
                if all_errored:
                    final_status = TestRunStatus.ERROR
                elif has_issues:
                    final_status = TestRunStatus.PARTIAL_FAILURE
                else:
                    final_status = TestRunStatus.COMPLETED
                db_session.query(DatabaseContinuousEvalTestRun).filter(
                    DatabaseContinuousEvalTestRun.id == test_run_id,
                ).update(
                    {"status": final_status, "updated_at": datetime.now()},
                    synchronize_session=False,
                )
                logger.info(
                    f"Test run {test_run_id} completed with status: {final_status}",
                )
            db_session.commit()

        except Exception as e:
            db_session.rollback()
            logger.error(
                f"Error incrementing test run counters for {test_run_id}: {e}",
                exc_info=True,
            )


CONTINUOUS_EVAL_QUEUE_SERVICE: ContinuousEvalQueueService | None = None


def get_continuous_eval_queue_service() -> ContinuousEvalQueueService | None:
    """Get the global continuous eval queue service instance."""
    return CONTINUOUS_EVAL_QUEUE_SERVICE


def initialize_continuous_eval_queue_service(
    num_workers: int = 4,
    override_execution_delay: Optional[int] = None,
) -> None:
    """Initialize and start the global continuous eval queue service."""
    global CONTINUOUS_EVAL_QUEUE_SERVICE
    if CONTINUOUS_EVAL_QUEUE_SERVICE is None:
        CONTINUOUS_EVAL_QUEUE_SERVICE = ContinuousEvalQueueService(
            num_workers,
            override_execution_delay,
        )
        CONTINUOUS_EVAL_QUEUE_SERVICE.start()


def shutdown_continuous_eval_queue_service() -> None:
    """Shutdown the global continuous eval queue service."""
    global CONTINUOUS_EVAL_QUEUE_SERVICE
    if CONTINUOUS_EVAL_QUEUE_SERVICE is not None:
        CONTINUOUS_EVAL_QUEUE_SERVICE.stop()
        CONTINUOUS_EVAL_QUEUE_SERVICE = None
