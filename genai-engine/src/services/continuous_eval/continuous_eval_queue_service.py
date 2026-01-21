import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from sqlalchemy.orm import Session

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from dependencies import get_db_session
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.internal_schemas import ContinuousEval
from schemas.request_schemas import BaseCompletionRequest
from utils.transform_executor import execute_transform

logger = logging.getLogger(__name__)


class ContinuousEvalJob:
    """Represents a continuous eval job to be executed."""

    def __init__(
        self,
        annotation_id: uuid.UUID,
        trace_id: str,
        continuous_eval_id: uuid.UUID,
        task_id: str,
        delay_seconds: int = 10,
    ):
        self.annotation_id = annotation_id
        self.trace_id = trace_id
        self.continuous_eval_id = continuous_eval_id
        self.task_id = task_id
        self.enqueued_at = datetime.now()
        self.delay_seconds = delay_seconds
        self.execute_at = time.time() + delay_seconds


class ContinuousEvalQueueService:
    """Service that manages async execution of continuous evals using ThreadPoolExecutor."""

    def __init__(
        self,
        num_workers: int = 4,
        override_execution_delay: Optional[int] = None,
    ):
        self.num_workers = num_workers
        self.background_thread: Optional[threading.Thread] = None
        self.executor: Optional[ThreadPoolExecutor] = None
        self.shutdown_event = threading.Event()
        self.override_execution_delay = override_execution_delay

    def start(self) -> None:
        """Start executor and background thread."""
        logger.info(
            f"Starting continuous eval queue service with {self.num_workers} workers",
        )

        # Create executor for job execution
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers)

        # Start background thread that checks for stale annotations
        self.background_thread = threading.Thread(
            target=self._background_loop,
            name="continuous-eval-background",
            daemon=True,
        )
        self.background_thread.start()

        logger.info("Continuous eval queue service started")

    def stop(self, timeout: int = 30) -> None:
        """Stop executor and background thread"""
        logger.info("Stopping continuous eval queue service")
        self.shutdown_event.set()

        if self.executor:
            self.executor.shutdown(wait=True, cancel_futures=True)

        if self.background_thread:
            self.background_thread.join(timeout=timeout)
            if self.background_thread.is_alive():
                logger.warning("Background thread did not shut down gracefully")

        logger.info("Continuous eval queue service stopped")

    def _submit_job(self, job: ContinuousEvalJob, wait_time: float) -> None:
        """Submit a job to the executor after the wait time."""
        if self.shutdown_event.is_set():
            logger.warning(f"Skipping job for trace {job.trace_id} due to shutdown")
            return

        if self.shutdown_event.wait(wait_time):
            return

        if not self.executor:
            logger.error(
                f"Cannot submit job for trace {job.trace_id}: executor is not initialized",
            )
            return

        self.executor.submit(self._execute_job, job)

    def enqueue(self, job: ContinuousEvalJob) -> None:
        """Schedule a job to be executed"""
        if self.override_execution_delay is not None:
            wait_time = (
                job.execute_at - job.delay_seconds + self.override_execution_delay
            )
        else:
            wait_time = job.execute_at

        wait_time = max(0, wait_time - time.time())
        if not self.executor:
            logger.error(
                f"Cannot submit job for trace {job.trace_id}: executor is not initialized. Start the continuous eval queue service first.",
            )
            raise ValueError(
                "Continuous eval queue service is not initialized. Start the continuous eval queue service first.",
            )
        self.executor.submit(self._submit_job, job, wait_time)

    def _background_loop(self) -> None:
        """Background thread that checks for stale pending annotations and re-queues them."""
        logger.info("Background thread started")

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

            for annotation, continuous_eval in stale_annotations:
                job = ContinuousEvalJob(
                    annotation_id=annotation.id,
                    trace_id=annotation.trace_id,
                    continuous_eval_id=annotation.continuous_eval_id,
                    task_id=continuous_eval.task_id,
                    delay_seconds=0,
                )
                self.enqueue(job)

            logger.info(f"Re-queued {len(stale_annotations)} stale annotations")

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
            continuous_eval = (
                db_session.query(DatabaseContinuousEval)
                .filter(DatabaseContinuousEval.id == job.continuous_eval_id)
                .first()
            )

            if not continuous_eval:
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
                continuous_eval.transform_id,
            )
            if not trace_transform:
                raise ValueError(f"Transform {continuous_eval.transform_id} not found")

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
                    annotation_description=f"Could not extract variables: {', '.join(transform_results.missing_variables)} using transform {continuous_eval.transform_id} on trace {job.trace_id}",
                )
                return

            # Get the mapping from transform var to eval var
            continuous_eval = ContinuousEval.from_db_model(continuous_eval)
            mapping_dict = {
                mapping.transform_variable: mapping.eval_variable
                for mapping in continuous_eval.transform_variable_mapping
            }

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
