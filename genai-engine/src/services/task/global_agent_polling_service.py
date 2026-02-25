import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Hashable, Optional

from arthur_common.models.agent_governance_schemas import (
    AgentCreationSource,
    GCPAgentCreationSource,
    TaskMetadata,
)
from arthur_common.models.enums import RegisteredAgentProvider
from sqlalchemy import func, text

from db_models import DatabaseTask
from dependencies import get_db_session
from repositories.configuration_repository import ConfigurationRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.service_name_mapping_repository import ServiceNameMappingRepository
from repositories.span_repository import SpanRepository
from repositories.task_polling_state_repository import TaskPollingStateRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.tasks_repository import TaskRepository
from schemas.agent_discovery_schemas import DiscoverAndPollResponse
from schemas.internal_schemas import Task
from services.agent_discovery_service import list_vertex_ai_agents
from services.base_queue_service import BaseQueueJob, BaseQueueService
from services.trace.external_trace_retrieval_service import (
    ExternalTraceRetrievalService,
)
from utils import constants
from utils.gcp import parse_gcp_resource_path
from utils.utils import get_env_var

logger = logging.getLogger(__name__)

# PostgreSQL session-level advisory lock key for polling leader election.
# Any stable int64 works; this value is unique to Arthur GenAI Engine polling.
POLLING_ADVISORY_LOCK_KEY = 17449340

# Time interval between polling loop iterations (defaults to 1 hour)
AGENTIC_POLLING_INTERVAL_SECONDS: int = int(
    get_env_var(
        constants.GENAI_ENGINE_AGENTIC_POLLING_INTERVAL_SECONDS_ENV_VAR,
        True,
    )
    or 3600,
)


class AgentPollingJob(BaseQueueJob):
    """Represents a polling job for a single task."""

    def __init__(self, task_id: str, delay_seconds: int = 0):
        super().__init__(delay_seconds)
        self.task_id = task_id


class GlobalAgentPollingService(BaseQueueService[AgentPollingJob]):
    """Global polling service that discovers agents and fetches traces in a single loop.

    Replaces the old per-task RegisteredAgentPollingService with a unified loop:
    1. Discovery phase: List Vertex AI agents, create tasks for new ones
    2. Fetch phase: Enqueue trace-fetch jobs for all eligible GCP tasks

    Eligibility: A GCP task is only polled if its gcp_project_id and gcp_region
    match the current GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION environment
    variables. Tasks from a different project/region are skipped with a warning.

    Error handling: Failed polls are logged but never block future polls.
    """

    job_model = AgentPollingJob
    service_name = "global_agent_polling_service"
    background_thread_name = "global-agent-polling-background"

    def _get_job_key(self, job: AgentPollingJob) -> Hashable:
        """Use task_id as the unique key for deduplication."""
        return job.task_id

    def _background_loop(self) -> None:
        """Background thread that runs discovery + polling at regular intervals.

        Uses a PostgreSQL session-level advisory lock to elect a single leader
        across all replicas. Only the replica that acquires the lock runs the
        discovery and polling loop. Non-leaders wait and retry each interval so
        they can take over if the leader crashes (the lock is released
        automatically when the leader's DB session closes).
        """
        logger.info(f"Background thread started for {self.service_name}")

        while not self.shutdown_event.is_set():
            leader_session = None
            try:
                leader_session = next(get_db_session())
                acquired = leader_session.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": POLLING_ADVISORY_LOCK_KEY},
                ).scalar()

                if not acquired:
                    logger.info(
                        "Another replica holds the polling leader lock, standing by"
                    )
                    self.shutdown_event.wait(timeout=AGENTIC_POLLING_INTERVAL_SECONDS)
                    continue

                logger.info(
                    "Acquired polling leader lock, running discovery + polling loop"
                )

                while not self.shutdown_event.is_set():
                    try:
                        self._discover_and_poll_agents()
                    except Exception as e:
                        logger.error(f"Error in background loop: {e}", exc_info=True)

                    if self.shutdown_event.wait(
                        timeout=AGENTIC_POLLING_INTERVAL_SECONDS
                    ):
                        break

            except Exception as e:
                logger.error(f"Error acquiring polling leader lock: {e}", exc_info=True)
            finally:
                if leader_session is not None:
                    leader_session.close()

        logger.info(f"Background thread stopped for {self.service_name}")

    def _discover_and_poll_agents(
        self, wait_for_completion: bool = False, timeout: Optional[float] = None
    ) -> DiscoverAndPollResponse:
        """Run a full discovery + polling cycle.

        Args:
            wait_for_completion: If True, block until all polling jobs complete.
            timeout: Maximum seconds to wait for jobs (only used if wait_for_completion=True).

        Returns:
            DiscoverAndPollResponse with discovered and traces_fetched counts.
        """
        discovered = self._discover_gcp_agents()
        traces_fetched = self._poll_all_gcp_tasks(wait_for_completion, timeout)
        return DiscoverAndPollResponse(
            status="completed",
            discovered=discovered,
            traces_fetched=traces_fetched,
        )

    def _discover_gcp_agents(self) -> int:
        """List Vertex AI agents and create tasks for newly discovered ones.

        Skips discovery if GOOGLE_CLOUD_PROJECT is not configured.

        Returns:
            Number of newly created tasks.
        """
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project_id:
            logger.debug("GOOGLE_CLOUD_PROJECT not set, skipping GCP agent discovery")
            return 0

        created_count = 0
        db_session = next(get_db_session())
        try:
            agents = list_vertex_ai_agents(project_id, location)

            if not agents:
                logger.info("No Vertex AI agents found during discovery")
                return 0

            logger.info(f"Discovered {len(agents)} Vertex AI agent(s)")

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
            mapping_repo = ServiceNameMappingRepository(db_session)
            polling_state_repo = TaskPollingStateRepository(db_session)

            for agent in agents:
                try:
                    api_resource = agent.api_resource
                    resource_name = getattr(api_resource, "name", "")
                    if not resource_name:
                        continue

                    _, region, engine_id = parse_gcp_resource_path(resource_name)
                    if not engine_id:
                        logger.warning(
                            f"Could not parse engine ID from resource: {resource_name}"
                        )
                        continue

                    # Check if a task already exists for this engine ID
                    logger.info(
                        f"Checking for existing task with engine_id={engine_id}"
                    )
                    existing_task = task_repository.find_by_gcp_engine_id(engine_id)
                    if existing_task:
                        continue

                    # Create task with GCP creation_source
                    display_name = (
                        getattr(api_resource, "display_name", None) or engine_id
                    )
                    task_metadata = TaskMetadata(
                        creation_source=AgentCreationSource(
                            root=GCPAgentCreationSource(
                                gcp_project_id=project_id,
                                gcp_region=region or location,
                                gcp_reasoning_engine_id=engine_id,
                            )
                        ),
                    )

                    task = Task(
                        id=str(uuid.uuid4()),
                        name=f"Vertex AI Agent: {display_name}",
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        is_agentic=True,
                        is_autocreated=True,
                        task_metadata=task_metadata,
                    )
                    created_task = task_repository.create_task(
                        task, with_default_rules=False
                    )

                    # Create service_name mapping using the resource path
                    mapping_repo.create_mapping(resource_name, created_task.id)

                    # Initialize polling state
                    polling_state_repo.get_or_create(created_task.id)

                    created_count += 1
                    logger.info(
                        f"Created task '{created_task.name}' (id={created_task.id}) "
                        f"for GCP engine {engine_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error processing discovered agent: {e}",
                        exc_info=True,
                    )
                    db_session.rollback()
                    continue

        except Exception as e:
            logger.error(f"Error during GCP agent discovery: {e}", exc_info=True)
        finally:
            db_session.close()

        return created_count

    def _is_task_eligible_for_polling(
        self,
        task_id: str,
        creation_source: GCPAgentCreationSource,
        current_project_id: str,
        current_location: str,
    ) -> bool:
        """Check if a GCP task is eligible for polling in the current environment.

        A task is eligible only if its gcp_project_id and gcp_region match
        the currently configured GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION.
        """
        if creation_source.gcp_project_id != current_project_id:
            logger.warning(
                f"Skipping task {task_id}: project mismatch "
                f"(task={creation_source.gcp_project_id}, "
                f"current={current_project_id})"
            )
            return False

        if creation_source.gcp_region != current_location:
            logger.warning(
                f"Skipping task {task_id}: region mismatch "
                f"(task={creation_source.gcp_region}, "
                f"current={current_location})"
            )
            return False

        return True

    def _poll_all_gcp_tasks(
        self, wait_for_completion: bool = False, timeout: Optional[float] = None
    ) -> int:
        """Enqueue trace-fetch jobs for all eligible GCP tasks.

        Finds all GCP tasks, checks eligibility (project/region match),
        and enqueues polling jobs. Failed polls are logged but never block
        future polls.

        Args:
            wait_for_completion: If True, block until all jobs complete.
            timeout: Maximum seconds to wait (only used if wait_for_completion=True).

        Returns:
            Number of traces fetched (0 for async mode, actual count for sync mode).
        """
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project_id:
            logger.debug("GOOGLE_CLOUD_PROJECT not set, skipping GCP task polling")
            return 0

        enqueued_count = 0
        db_session = next(get_db_session())
        try:
            # Find all tasks with GCP creation_source
            gcp_tasks = (
                db_session.query(DatabaseTask)
                .filter(
                    DatabaseTask.is_agentic == True,
                    DatabaseTask.archived == False,
                    func.json_extract_path_text(
                        DatabaseTask.task_metadata,
                        "creation_source",
                        "type",
                    )
                    == "GCP",
                )
                .all()
            )

            if not gcp_tasks:
                logger.info("No GCP tasks found for polling")
                return 0

            logger.info(f"Found {len(gcp_tasks)} GCP task(s), checking eligibility")

            # Ensure polling state exists and collect eligible jobs
            polling_state_repo = TaskPollingStateRepository(db_session)
            skipped_count = 0
            jobs_to_enqueue = []

            for db_task in gcp_tasks:
                metadata = (
                    TaskMetadata.model_validate(db_task.task_metadata)
                    if db_task.task_metadata
                    else None
                )
                creation_source = (
                    metadata.creation_source.root
                    if metadata and metadata.creation_source
                    else None
                )
                if not isinstance(creation_source, GCPAgentCreationSource):
                    skipped_count += 1
                    continue

                if not self._is_task_eligible_for_polling(
                    db_task.id, creation_source, project_id, location
                ):
                    skipped_count += 1
                    continue

                polling_state_repo.get_or_create(db_task.id)
                job = AgentPollingJob(task_id=db_task.id)
                jobs_to_enqueue.append(job)

            # Execute based on mode
            if wait_for_completion:
                # Synchronous mode: enqueue and wait for all jobs
                from concurrent.futures import wait

                futures_to_jobs = {}
                for job in jobs_to_enqueue:
                    enqueued, future = self.enqueue(job)
                    if enqueued and future:
                        futures_to_jobs[future] = job

                if not futures_to_jobs:
                    # All jobs were skipped (already active)
                    logger.info(
                        f"All {len(jobs_to_enqueue)} jobs skipped (already active), "
                        f"{skipped_count} ineligible"
                    )
                    return 0

                # Wait for all futures to complete
                done, not_done = wait(futures_to_jobs.keys(), timeout=timeout)

                # Aggregate trace counts from completed jobs
                total_traces = 0
                failures = 0
                for future in done:
                    job = futures_to_jobs[future]
                    try:
                        trace_count = future.result()
                        total_traces += trace_count
                    except Exception as e:
                        failures += 1
                        logger.error(
                            f"Polling failed for task {job.task_id}: {e}",
                            exc_info=True,
                        )

                # Log completion summary
                log_parts = [
                    f"Synchronous polling completed: {len(done)} succeeded, "
                    f"{failures} failed"
                ]
                if not_done:
                    log_parts.append(f"{len(not_done)} timed out")
                if skipped_count > 0:
                    log_parts.append(
                        f"{skipped_count} skipped (ineligible or already active)"
                    )
                logger.info(", ".join(log_parts))

                # Raise timeout error if any jobs didn't complete
                if not_done:
                    timed_out_task_ids = [
                        futures_to_jobs[future].task_id for future in not_done
                    ]
                    raise TimeoutError(
                        f"{len(not_done)} polling job(s) timed out after {timeout}s. "
                        f"Task IDs: {', '.join(timed_out_task_ids)}"
                    )

                return total_traces
            else:
                # Asynchronous mode: enqueue and return (original behavior)
                enqueued_count = 0
                for job in jobs_to_enqueue:
                    enqueued, _ = self.enqueue(job)
                    if enqueued:
                        enqueued_count += 1

                log_parts = [f"Enqueued {enqueued_count} polling jobs"]
                already_active = len(jobs_to_enqueue) - enqueued_count
                if skipped_count > 0:
                    log_parts.append(f"{skipped_count} skipped (ineligible)")
                if already_active > 0:
                    log_parts.append(f"{already_active} already active")
                logger.info(", ".join(log_parts))

                return 0  # Unknown trace count for async mode

        except Exception as e:
            logger.error(f"Error enqueuing GCP polling jobs: {e}", exc_info=True)
            if wait_for_completion:
                raise
            return 0
        finally:
            db_session.close()

    def _execute_job(self, job: AgentPollingJob) -> int:
        """Fetch traces for a single task.

        On success: updates last_fetched.
        On failure: logs the error for observability but does NOT
        update polling state — the next loop iteration will retry automatically.

        Returns:
            int: Number of traces fetched for this task.
        """

        db_session = next(get_db_session())
        try:
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
            task = task_repository.get_task_by_id(job.task_id)
            if not task:
                logger.error(f"Task {job.task_id} not found, skipping poll")
                return 0

            if (
                task.task_metadata is None
                or task.task_metadata.creation_source is None
                or not isinstance(
                    task.task_metadata.creation_source.root, GCPAgentCreationSource
                )
            ):
                logger.warning(f"Task {job.task_id} is not a GCP task, skipping poll")
                return 0

            creation_source = task.task_metadata.creation_source.root

            # Determine time range
            polling_state_repo = TaskPollingStateRepository(db_session)
            polling_state = polling_state_repo.get_or_create(task.id)

            now = datetime.now()
            if polling_state.last_fetched is None:
                start_time = now - timedelta(days=30)
                logger.info(
                    f"Polling task {task.id} ({task.name}), "
                    f"fetching data from last 30 days"
                )
            else:
                start_time = polling_state.last_fetched
                logger.info(
                    f"Polling task {task.id} ({task.name}) "
                    f"from {start_time} to {now}"
                )

            # Fetch and ingest traces page by page
            external_trace_service = ExternalTraceRetrievalService()
            tasks_metrics_repository = TasksMetricsRepository(db_session)
            span_repository = SpanRepository(
                db_session,
                tasks_metrics_repository,
                metric_repository,
            )

            total_trace_count = 0
            for page_traces in external_trace_service.fetch_traces_from_cloud_trace(
                task_id=task.id,
                project_id=creation_source.gcp_project_id,
                reasoning_engine_id=creation_source.gcp_reasoning_engine_id,
                start_time=start_time,
                end_time=now,
                timeout=60,
            ):
                span_repository.convert_and_send_traces_from_external_provider(
                    traces=page_traces,
                    provider=RegisteredAgentProvider.GCP,
                    task_id=task.id,
                )
                total_trace_count += len(page_traces)

            if total_trace_count == 0:
                logger.info(
                    f"No traces found for task {task.id} ({task.name}) "
                    f"between {start_time} and {now}"
                )

            # Update polling state (whether traces were found or not)
            polling_state_repo.update_last_fetched(task.id, now)
            logger.info(
                f"Polling completed for task {task.id} ({task.name}), "
                f"processed {total_trace_count} trace(s)"
            )

            return total_trace_count

        except Exception as e:
            # Log for observability — do not persist error state.
            # The next polling loop iteration will retry this task automatically.
            logger.error(
                f"Polling failed for task {job.task_id}: {e}",
                exc_info=True,
                extra={"task_id": job.task_id},
            )
            return 0
        finally:
            db_session.close()


GLOBAL_AGENT_POLLING_SERVICE: GlobalAgentPollingService | None = None


def get_global_agent_polling_service() -> GlobalAgentPollingService | None:
    """Get the global agent polling service instance."""
    return GLOBAL_AGENT_POLLING_SERVICE


def initialize_global_agent_polling_service(
    num_workers: int = 4,
    override_execution_delay: Optional[int] = None,
) -> None:
    """Initialize and start the global agent polling service."""
    global GLOBAL_AGENT_POLLING_SERVICE
    if GLOBAL_AGENT_POLLING_SERVICE is None:
        GLOBAL_AGENT_POLLING_SERVICE = GlobalAgentPollingService(
            num_workers,
            override_execution_delay,
        )
        GLOBAL_AGENT_POLLING_SERVICE.start()


def shutdown_global_agent_polling_service() -> None:
    """Shutdown the global agent polling service."""
    global GLOBAL_AGENT_POLLING_SERVICE
    if GLOBAL_AGENT_POLLING_SERVICE is not None:
        GLOBAL_AGENT_POLLING_SERVICE.stop()
        GLOBAL_AGENT_POLLING_SERVICE = None
