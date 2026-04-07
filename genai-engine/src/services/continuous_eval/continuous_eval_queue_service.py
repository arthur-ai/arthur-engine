import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from sqlalchemy.orm import Session

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.continuous_eval_test_run_models import DatabaseContinuousEvalTestRun
from db_models.llm_eval_models import DatabaseContinuousEval
from dependencies import get_db_session
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.internal_schemas import ContinuousEval
from schemas.request_schemas import BaseCompletionRequest
from services.base_queue_service import BaseQueueJob, BaseQueueService
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
                    DatabaseAgenticAnnotation.test_run_id.is_(None),
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
        """Execute a single evaluation job."""
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

        # If this annotation belongs to a test run, update the test run counters
        if db_annotation.test_run_id:
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
        """Atomically increment test run counters after an annotation completes."""
        try:
            update_values: dict = {
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

            # Check if test run is complete and update status
            db_test_run = (
                db_session.query(DatabaseContinuousEvalTestRun)
                .filter(DatabaseContinuousEvalTestRun.id == test_run_id)
                .first()
            )
            if db_test_run and db_test_run.completed_count >= db_test_run.total_count:
                has_issues = (
                    db_test_run.error_count > 0 or db_test_run.skipped_count > 0
                )
                final_status = "partial_failure" if has_issues else "completed"
                db_session.query(DatabaseContinuousEvalTestRun).filter(
                    DatabaseContinuousEvalTestRun.id == test_run_id,
                ).update(
                    {"status": final_status, "updated_at": datetime.now()},
                    synchronize_session=False,
                )
                db_session.commit()
                logger.info(
                    f"Test run {test_run_id} completed with status: {final_status}",
                )

        except Exception as e:
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
