import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.enums import (
    AgenticAnnotationType,
    ContinuousEvalRunStatus,
    RuleResultEnum,
    RuleType,
)
from sqlalchemy.orm import Session

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from dependencies import get_db_session
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.internal_schemas import ContinuousEval, ValidationRequest
from schemas.request_schemas import BaseCompletionRequest
from scorer.score import ScorerClient
from services.base_queue_service import BaseQueueJob, BaseQueueService
from services.continuous_eval.rule_ce_evaluator import RuleCEEvaluator
from utils.transform_executor import execute_transform

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        num_workers: int,
        override_execution_delay: Optional[int] = None,
        scorer_client: Optional[ScorerClient] = None,
    ) -> None:
        super().__init__(num_workers, override_execution_delay)
        self._rule_ce_evaluator: Optional[RuleCEEvaluator] = (
            RuleCEEvaluator(scorer_client) if scorer_client is not None else None
        )

    def _get_rule_ce_evaluator(self) -> RuleCEEvaluator:
        """Lazily obtain the RuleCEEvaluator, creating it from the global scorer client if needed."""
        if self._rule_ce_evaluator is None:
            from dependencies import get_scorer_client

            self._rule_ce_evaluator = RuleCEEvaluator(get_scorer_client())
        return self._rule_ce_evaluator

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
        """Execute a single evaluation job, dispatching on evaluator_type."""
        db_session = next(get_db_session())
        try:
            # Check if annotation exists
            annotation = (
                db_session.query(DatabaseAgenticAnnotation)
                .filter(DatabaseAgenticAnnotation.id == job.annotation_id)
                .first()
            )

            if not annotation:
                raise ValueError(f"Annotation {job.annotation_id} not found")
            if (
                annotation.annotation_type
                != AgenticAnnotationType.CONTINUOUS_EVAL.value
            ):
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
                raise ValueError(
                    f"Annotation {job.annotation_id} is running or has already finished executing",
                )

            # Load the continuous eval configuration
            db_continuous_eval = (
                db_session.query(DatabaseContinuousEval)
                .filter(DatabaseContinuousEval.id == job.continuous_eval_id)
                .first()
            )

            if not db_continuous_eval:
                raise ValueError(f"Continuous eval {job.continuous_eval_id} not found")

            evaluator_type = getattr(db_continuous_eval, "evaluator_type", "llm") or "llm"

            if evaluator_type == "rule":
                self._execute_rule_job(db_session, job, db_continuous_eval)
            else:
                self._execute_llm_job(db_session, job, db_continuous_eval)

        except Exception as e:
            logger.error(
                f"Error executing job for trace {job.trace_id}: {e}",
                exc_info=True,
            )
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.ERROR.value,
                annotation_description=str(e),
            )
            raise e
        finally:
            db_session.close()

    # ------------------------------------------------------------------
    # LLM evaluator path (unchanged logic, extracted for clarity)
    # ------------------------------------------------------------------

    def _execute_llm_job(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
        db_continuous_eval: DatabaseContinuousEval,
    ) -> None:
        """Execute the LLM-based continuous eval path."""
        # Validate trace exists
        tasks_metrics_repository = TasksMetricsRepository(db_session)
        metric_repository = MetricRepository(db_session)
        span_repository = SpanRepository(
            db_session,
            tasks_metrics_repository,
            metric_repository,
        )

        trace = span_repository.get_trace_by_id(job.trace_id)
        if not trace:
            raise ValueError(f"Trace {job.trace_id} not found")

        # Verify the transform exists
        trace_transform_repository = TraceTransformRepository(db_session)
        trace_transform = trace_transform_repository.get_transform_by_id(
            db_continuous_eval.transform_id,
        )
        if not trace_transform:
            raise ValueError(
                f"Transform {db_continuous_eval.transform_id} not found",
            )

        # Execute the transform over the trace
        transform_results = execute_transform(trace, trace_transform.definition)
        if len(transform_results.missing_spans) > 0:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=f"Spans {', '.join(transform_results.missing_spans)} not found in trace {job.trace_id} skipping continuous eval execution for eval {job.continuous_eval_id}",
            )
            return
        if len(transform_results.missing_variables) > 0:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.ERROR.value,
                annotation_description=f"Could not extract variables: {', '.join(transform_results.missing_variables)} using transform {db_continuous_eval.transform_id} on trace {job.trace_id}",
            )
            return

        # Get the mapping from transform var to eval var
        continuous_eval = ContinuousEval.from_db_model(db_continuous_eval)
        mapping_dict: dict[str, str] = {}
        for mapping in continuous_eval.transform_variable_mapping:
            mapping_dict[mapping.transform_variable] = mapping.eval_variable

        # Build the completion request variables
        completion_request_variables = []
        mapped_eval_vars = set()
        for variable in transform_results.variables:
            if variable.name in mapping_dict:
                completion_request_variables.append(
                    VariableTemplateValue(
                        name=mapping_dict[variable.name],
                        value=variable.value,
                    ),
                )
                mapped_eval_vars.add(mapping_dict[variable.name])

        llm_eval_repository = LLMEvalsRepository(db_session)
        llm_eval = llm_eval_repository.get_llm_item(
            continuous_eval.task_id,
            continuous_eval.llm_eval_name,
            str(continuous_eval.llm_eval_version),
        )

        # Validate that the mapped eval vars match the llm eval vars
        if mapped_eval_vars != set(llm_eval.variables):
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=f"Mapped eval variables: {', '.join(mapped_eval_vars)} do not match LLM eval variables: {', '.join(llm_eval.variables)}",
            )
            return

        completion_request = BaseCompletionRequest(
            variables=completion_request_variables,
        )

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

        llm_eval_run_result = llm_eval_repository.run_llm_eval(
            job.task_id,
            continuous_eval.llm_eval_name,
            str(continuous_eval.llm_eval_version),
            completion_request,
        )
        run_status = (
            ContinuousEvalRunStatus.PASSED.value
            if llm_eval_run_result.score == 1
            else ContinuousEvalRunStatus.FAILED.value
        )
        llm_eval_run_result_cost = (
            float(llm_eval_run_result.cost) if llm_eval_run_result.cost else None
        )
        self._update_annotation_status(
            db_session,
            job.annotation_id,
            run_status,
            input_variables=completion_request_variables,
            annotation_score=llm_eval_run_result.score,
            annotation_description=llm_eval_run_result.reason,
            cost=llm_eval_run_result_cost,
        )

    # ------------------------------------------------------------------
    # Rule evaluator path (BE4)
    # ------------------------------------------------------------------

    def _execute_rule_job(
        self,
        db_session: Session,
        job: ContinuousEvalJob,
        db_continuous_eval: DatabaseContinuousEval,
    ) -> None:
        """Execute a rule-based continuous eval against the trace.

        Dispatches to RuleCEEvaluator for PII_DATA, PROMPT_INJECTION, and
        TOXICITY rule types.  Results are stored as annotation_score (1=pass,
        0=fail) and annotation_description (JSON-serialised rule details).
        """
        rule_type_str = getattr(db_continuous_eval, "rule_type", None)
        if not rule_type_str:
            raise ValueError(
                f"Continuous eval {job.continuous_eval_id} has evaluator_type='rule' "
                "but no rule_type is set"
            )

        try:
            rule_type = RuleType(rule_type_str)
        except ValueError:
            raise ValueError(
                f"Unknown rule_type '{rule_type_str}' on continuous eval {job.continuous_eval_id}"
            )

        rule_config = getattr(db_continuous_eval, "rule_config", None) or {}

        # Validate trace exists
        tasks_metrics_repository = TasksMetricsRepository(db_session)
        metric_repository = MetricRepository(db_session)
        span_repository = SpanRepository(
            db_session,
            tasks_metrics_repository,
            metric_repository,
        )

        trace = span_repository.get_trace_by_id(job.trace_id)
        if not trace:
            raise ValueError(f"Trace {job.trace_id} not found")

        # Verify the transform exists
        trace_transform_repository = TraceTransformRepository(db_session)
        trace_transform = trace_transform_repository.get_transform_by_id(
            db_continuous_eval.transform_id,
        )
        if not trace_transform:
            raise ValueError(
                f"Transform {db_continuous_eval.transform_id} not found",
            )

        # Execute the transform to extract text variables from the trace
        transform_results = execute_transform(trace, trace_transform.definition)
        if len(transform_results.missing_spans) > 0:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=(
                    f"Spans {', '.join(transform_results.missing_spans)} not found in "
                    f"trace {job.trace_id}, skipping rule eval for eval {job.continuous_eval_id}"
                ),
            )
            return
        if len(transform_results.missing_variables) > 0:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.ERROR.value,
                annotation_description=(
                    f"Could not extract variables: {', '.join(transform_results.missing_variables)} "
                    f"using transform {db_continuous_eval.transform_id} on trace {job.trace_id}"
                ),
            )
            return

        # Build a ValidationRequest from the transform variable mapping.
        # The transform_variable_mapping for rule CEs maps transform var names
        # to 'prompt' or 'response' (the fields on ValidationRequest).
        continuous_eval = ContinuousEval.from_db_model(db_continuous_eval)
        mapping_dict: dict[str, str] = {
            m.transform_variable: m.eval_variable
            for m in continuous_eval.transform_variable_mapping
        }
        extracted: dict[str, str] = {v.name: v.value for v in transform_results.variables}

        prompt_text: Optional[str] = None
        response_text: Optional[str] = None
        for transform_var, eval_var in mapping_dict.items():
            value = extracted.get(transform_var)
            if eval_var == "prompt":
                prompt_text = value
            elif eval_var == "response":
                response_text = value

        if prompt_text is None and response_text is None:
            self._update_annotation_status(
                db_session,
                job.annotation_id,
                ContinuousEvalRunStatus.SKIPPED.value,
                annotation_description=(
                    "No 'prompt' or 'response' variable found in transform_variable_mapping "
                    f"for rule CE {job.continuous_eval_id}"
                ),
            )
            return

        validation_request = ValidationRequest(
            prompt=prompt_text,
            response=response_text,
        )

        # Atomically claim the annotation (PENDING -> RUNNING)
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

        # Run the rule via RuleCEEvaluator
        rule_score = self._get_rule_ce_evaluator().evaluate(
            rule_type=rule_type,
            rule_config=rule_config,
            validation_request=validation_request,
        )

        # Map rule result -> annotation status and score
        run_status, annotation_score = self._map_rule_result_to_status(rule_score.result)

        # Serialise rule details as JSON for annotation_description
        annotation_description: Optional[str] = None
        if rule_score.details is not None:
            annotation_description = rule_score.details.model_dump_json(exclude_none=True)

        self._update_annotation_status(
            db_session,
            job.annotation_id,
            run_status,
            annotation_score=annotation_score,
            annotation_description=annotation_description,
        )

    @staticmethod
    def _map_rule_result_to_status(
        result: RuleResultEnum,
    ) -> tuple[str, Optional[int]]:
        """Map a RuleResultEnum to a (ContinuousEvalRunStatus value, annotation_score) pair."""
        if result == RuleResultEnum.PASS:
            return ContinuousEvalRunStatus.PASSED.value, 1
        elif result == RuleResultEnum.FAIL:
            return ContinuousEvalRunStatus.FAILED.value, 0
        elif result == RuleResultEnum.SKIPPED:
            return ContinuousEvalRunStatus.SKIPPED.value, None
        else:
            # UNAVAILABLE / PARTIALLY_UNAVAILABLE
            return ContinuousEvalRunStatus.ERROR.value, None

    def _update_annotation_status(
        self,
        db_session: Session,
        annotation_id: uuid.UUID,
        run_status: str,
        annotation_score: Optional[int] = None,
        annotation_description: Optional[str] = None,
        input_variables: Optional[list[VariableTemplateValue]] = None,
        cost: Optional[float] = None,
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
        if input_variables is not None:
            db_annotation.input_variables = [
                variable.model_dump() for variable in input_variables
            ]
        if cost is not None:
            db_annotation.cost = cost

        db_session.commit()
        logger.debug(f"Updated annotation {annotation_id} to status {run_status}")


CONTINUOUS_EVAL_QUEUE_SERVICE: ContinuousEvalQueueService | None = None


def get_continuous_eval_queue_service() -> ContinuousEvalQueueService | None:
    """Get the global continuous eval queue service instance."""
    return CONTINUOUS_EVAL_QUEUE_SERVICE


def initialize_continuous_eval_queue_service(
    num_workers: int = 4,
    override_execution_delay: Optional[int] = None,
    scorer_client: Optional[ScorerClient] = None,
) -> None:
    """Initialize and start the global continuous eval queue service."""
    global CONTINUOUS_EVAL_QUEUE_SERVICE
    if CONTINUOUS_EVAL_QUEUE_SERVICE is None:
        CONTINUOUS_EVAL_QUEUE_SERVICE = ContinuousEvalQueueService(
            num_workers,
            override_execution_delay,
            scorer_client=scorer_client,
        )
        CONTINUOUS_EVAL_QUEUE_SERVICE.start()


def shutdown_continuous_eval_queue_service() -> None:
    """Shutdown the global continuous eval queue service."""
    global CONTINUOUS_EVAL_QUEUE_SERVICE
    if CONTINUOUS_EVAL_QUEUE_SERVICE is not None:
        CONTINUOUS_EVAL_QUEUE_SERVICE.stop()
        CONTINUOUS_EVAL_QUEUE_SERVICE = None
