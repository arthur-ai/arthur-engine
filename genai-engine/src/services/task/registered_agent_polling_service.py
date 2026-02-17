import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from arthur_common.models.enums import AgentPollingStatus, RegisteredAgentProvider
from google.api_core.exceptions import GoogleAPIError
from sqlalchemy.orm import Session

from db_models.agent_polling_models import DatabaseAgentPollingData
from dependencies import get_db_session
from repositories.configuration_repository import ConfigurationRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.tasks_repository import TaskRepository
from schemas.internal_schemas import AgentPollingData
from services.base_queue_service import BaseQueueJob, BaseQueueService
from services.trace.external_trace_retrieval_service import (
    ExternalTraceRetrievalService,
)
from utils import constants
from utils.utils import get_env_var

logger = logging.getLogger(__name__)

# Time interval agentic polling jobs (defaults to 1 hour)
AGENTIC_POLLING_INTERVAL_SECONDS: int = int(
    get_env_var(
        constants.GENAI_ENGINE_AGENTIC_POLLING_INTERVAL_SECONDS_ENV_VAR,
        True,
    )
    or 3600,
)


class AgentPollingJob(BaseQueueJob):
    """
    Represents a registered agent polling job to be executed.

    *Note: The delay_seconds is not currently used for this job. It is kept for compatibility with the base class
    and for potential future use cases that may require a delay to be implemented.
    """

    def __init__(
        self,
        agent_polling_data_id: uuid.UUID,
        delay_seconds: int = 0,
    ):
        super().__init__(delay_seconds)
        self.agent_polling_data_id = agent_polling_data_id


class RegisteredAgentPollingService(BaseQueueService[AgentPollingJob]):
    """Service that manages async execution of registered agent polling using ThreadPoolExecutor."""

    job_model = AgentPollingJob
    service_name = "registered_agent_polling_service"
    background_thread_name = "registered-agent-polling-background"

    def _get_job_key(self, job: AgentPollingJob) -> uuid.UUID:
        """Use agent_polling_data_id as the unique key for deduplication."""
        return job.agent_polling_data_id

    def _background_loop(self) -> None:
        """Background thread that continuously polls for new traces for registered agents."""
        logger.info(f"Background thread started for {self.service_name}")

        while not self.shutdown_event.is_set():
            try:
                # Checks for new traces once per AGENTIC_POLLING_INTERVAL_SECONDS
                if self.shutdown_event.wait(timeout=AGENTIC_POLLING_INTERVAL_SECONDS):
                    break

                # Poll all registered agents
                self._poll_registered_agents()

            except Exception as e:
                logger.error(f"Error in background loop: {e}", exc_info=True)

        logger.info(f"Background thread stopped for {self.service_name}")

    def _update_agent_polling_data_status(
        self,
        db_session: Session,
        agent_polling_data_id: uuid.UUID,
        status: AgentPollingStatus,
        last_fetched: Optional[datetime] = None,
        error_message: Optional[str] = None,
        failed_runs: Optional[int] = None,
    ) -> None:
        """Update agent polling data with execution results."""
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data_id)
            .first()
        )

        if not db_agent_polling_data:
            raise ValueError(f"Agent polling data {agent_polling_data_id} not found")

        db_agent_polling_data.status = status.value
        db_agent_polling_data.updated_at = datetime.now()
        db_agent_polling_data.error_message = error_message

        if failed_runs is not None:
            db_agent_polling_data.failed_runs = failed_runs
        if last_fetched is not None:
            db_agent_polling_data.last_fetched = last_fetched

        db_session.commit()
        logger.debug(
            f"Successfully updated agent polling data {agent_polling_data_id}. Status is {status}",
        )

    def _poll_registered_agents(self) -> None:
        """Poll for new traces for registered agents."""
        db_session = next(get_db_session())
        try:
            # Get all agent polling data where last_fetched is not null and status is IDLE
            # Use FOR UPDATE SKIP LOCKED to prevent race conditions when multiple nodes poll
            registered_agent_polling_data = (
                db_session.query(DatabaseAgentPollingData)
                .filter(
                    DatabaseAgentPollingData.status == AgentPollingStatus.IDLE,
                )
                .with_for_update(skip_locked=True)
                .all()
            )

            if not registered_agent_polling_data:
                logger.info("No registered agents found, skipping polling")
                return

            logger.info(
                f"Found {len(registered_agent_polling_data)} registered agents to poll",
            )

            enqueued_count = 0
            for agent_data in registered_agent_polling_data:
                # Create a job to poll for new data
                job = AgentPollingJob(
                    agent_polling_data_id=agent_data.id,
                )
                if self.enqueue(job):
                    # Set status to PENDING only if successfully enqueued
                    self._update_agent_polling_data_status(
                        db_session,
                        agent_data.id,
                        AgentPollingStatus.PENDING,
                    )
                    enqueued_count += 1

            if enqueued_count > 0:
                info_message = f"Enqueued {enqueued_count} polling jobs"
                info_message += (
                    f" ({len(registered_agent_polling_data) - enqueued_count} already active)"
                    if len(registered_agent_polling_data) - enqueued_count > 0
                    else ""
                )
                logger.info(info_message)

        except Exception as e:
            logger.error(f"Error polling registered agents: {e}", exc_info=True)
            db_session.rollback()
        finally:
            db_session.close()

    def _execute_job(self, job: AgentPollingJob) -> None:
        """Execute a single polling job."""
        db_session = next(get_db_session())
        try:
            # Get the agent polling data
            db_agent_polling_data = (
                db_session.query(DatabaseAgentPollingData)
                .filter(DatabaseAgentPollingData.id == job.agent_polling_data_id)
                .first()
            )
            if not db_agent_polling_data:
                raise ValueError(
                    f"Agent polling data {job.agent_polling_data_id} not found",
                )

            if db_agent_polling_data.status == AgentPollingStatus.RUNNING.value:
                logger.info(
                    f"Agent polling data {job.agent_polling_data_id} is already running, skipping",
                )
                return
            if db_agent_polling_data.status == AgentPollingStatus.ERROR.value:
                logger.info(
                    f"Agent polling data {job.agent_polling_data_id} has failed, skipping",
                )
                return

            agent_polling_data = AgentPollingData.from_database_model(
                db_agent_polling_data,
            )

            # Get the task
            rule_repository = RuleRepository(db_session)
            metric_repository = MetricRepository(db_session)
            configuration_repository = ConfigurationRepository(db_session)
            application_config = configuration_repository.get_configurations()
            task_repository = TaskRepository(
                db_session,
                rule_repository,
                metric_repository,
                application_config,
            )
            task = task_repository.get_task_by_id(agent_polling_data.task_id)
            if not task:
                raise ValueError(f"Task {agent_polling_data.task_id} not found")
            if task.task_metadata is None:
                raise ValueError(
                    f"Task {agent_polling_data.task_id} has no task metadata",
                )

            # Determine the time range to poll
            now = datetime.now()
            if agent_polling_data.last_fetched is None:
                # First time polling - get data from last 30 days
                start_time = now - timedelta(days=30)
                logger.info(
                    f"Polling agent {job.agent_polling_data_id}, fetching data from last 30 days",
                )
            else:
                # Subsequent poll - get data from last_fetched to now
                start_time = agent_polling_data.last_fetched
                logger.info(
                    f"Polling agent {job.agent_polling_data_id} from {start_time} to {now}",
                )

            # Fetch traces from external source
            external_trace_retrieval_service = ExternalTraceRetrievalService()

            self._update_agent_polling_data_status(
                db_session,
                job.agent_polling_data_id,
                AgentPollingStatus.RUNNING,
            )

            # Check provider and call appropriate polling method
            traces = []
            if task.task_metadata.provider == RegisteredAgentProvider.GCP:
                logger.info(
                    f"Polling GCP agent {job.agent_polling_data_id} for traces between {start_time} and {now}",
                )

                if task.task_metadata.gcp_metadata is None:
                    raise ValueError(
                        "GCP metadata are required for GCP provider",
                    )
                traces = external_trace_retrieval_service.fetch_traces_from_cloud_trace(
                    task_id=task.id,
                    project_id=task.task_metadata.gcp_metadata.project_id,
                    resource_id=task.task_metadata.gcp_metadata.resource_id,
                    start_time=start_time,
                    end_time=now,
                    timeout=60,  # 1 minute timeout
                )
            else:
                logger.warning(
                    f"Unsupported provider '{task.task_metadata.provider}', skipping polling",
                )

            if len(traces) == 0:
                logger.info(
                    f"No traces found for agent {job.agent_polling_data_id} between {start_time} and {now}",
                )
                self._update_agent_polling_data_status(
                    db_session,
                    job.agent_polling_data_id,
                    AgentPollingStatus.IDLE,
                    last_fetched=now,
                    failed_runs=0,
                )
                logger.info(
                    f"Updated last_fetched for agent {job.agent_polling_data_id} to {now}",
                )
                logger.info(f"Polling completed for {job.agent_polling_data_id}")
                return

            tasks_metrics_repository = TasksMetricsRepository(db_session)
            span_repository = SpanRepository(
                db_session,
                tasks_metrics_repository,
                metric_repository,
            )
            span_repository.convert_and_send_traces_from_external_provider(
                traces=traces,
                provider=task.task_metadata.provider,
                task_id=task.id,
            )

            # Update last_fetched timestamp on the existing database record
            self._update_agent_polling_data_status(
                db_session,
                job.agent_polling_data_id,
                AgentPollingStatus.IDLE,
                last_fetched=now,
                failed_runs=0,
            )
            logger.info(
                f"Updated last_fetched for agent {job.agent_polling_data_id} to {now}",
            )
            logger.info(f"Polling completed for {job.agent_polling_data_id}")

        except GoogleAPIError as e:
            logger.error(
                f"Error while fetching traces for agent {job.agent_polling_data_id}: {e}",
            )
            failed_runs = agent_polling_data.failed_runs + 1

            # Allow up to 5 timeouts before marking as ERROR permanently
            if failed_runs >= 5:
                logger.error(
                    f"Agent {job.agent_polling_data_id} has exceeded maximum failed runs (5), marking as ERROR",
                )
                self._update_agent_polling_data_status(
                    db_session,
                    job.agent_polling_data_id,
                    AgentPollingStatus.ERROR,
                    error_message=f"Exceeded maximum failed runs (5). Last error: {str(e)}",
                    failed_runs=failed_runs,
                )
                raise e
            else:
                logger.warning(
                    f"Agent {job.agent_polling_data_id} failed ({failed_runs}/5 allowed attempts), will retry on next poll",
                )
                self._update_agent_polling_data_status(
                    db_session,
                    job.agent_polling_data_id,
                    AgentPollingStatus.IDLE,
                    error_message=f"Error while fetching traces (attempt {failed_runs}/5): {str(e)}",
                    failed_runs=failed_runs,
                )
                # Don't raise - allow retry on next poll
        except Exception as e:
            logger.error(f"Error executing polling job: {e}", exc_info=True)
            self._update_agent_polling_data_status(
                db_session,
                job.agent_polling_data_id,
                AgentPollingStatus.ERROR,
                error_message=str(e),
            )
            raise e
        finally:
            db_session.close()


REGISTERED_AGENT_POLLING_SERVICE: RegisteredAgentPollingService | None = None


def get_registered_agent_polling_service() -> RegisteredAgentPollingService | None:
    """Get the global registered agent polling service instance."""
    return REGISTERED_AGENT_POLLING_SERVICE


def initialize_registered_agent_polling_service(
    num_workers: int = 4,
    override_execution_delay: Optional[int] = None,
) -> None:
    """Initialize and start the global registered agent polling service."""
    global REGISTERED_AGENT_POLLING_SERVICE
    if REGISTERED_AGENT_POLLING_SERVICE is None:
        REGISTERED_AGENT_POLLING_SERVICE = RegisteredAgentPollingService(
            num_workers,
            override_execution_delay,
        )
        REGISTERED_AGENT_POLLING_SERVICE.start()


def shutdown_registered_agent_polling_service() -> None:
    """Shutdown the global registered agent polling service."""
    global REGISTERED_AGENT_POLLING_SERVICE
    if REGISTERED_AGENT_POLLING_SERVICE is not None:
        REGISTERED_AGENT_POLLING_SERVICE.stop()
        REGISTERED_AGENT_POLLING_SERVICE = None
