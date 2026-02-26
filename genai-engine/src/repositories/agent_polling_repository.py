import logging

from arthur_common.models.agent_governance_schemas import GCPAgentCreationSource
from fastapi import HTTPException
from sqlalchemy.orm import Session

from repositories.configuration_repository import ConfigurationRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from services.task.global_agent_polling_service import (
    AgentPollingJob,
    get_global_agent_polling_service,
)

logger = logging.getLogger(__name__)


class AgentPollingRepository:
    def __init__(self, db_session: Session):
        """Initializes repository for agent polling operations."""
        self.db_session = db_session

        rule_repository = RuleRepository(db_session)
        metric_repository = MetricRepository(db_session)
        configuration_repository = ConfigurationRepository(db_session)
        application_config = configuration_repository.get_configurations()
        self.task_repository = TaskRepository(
            db_session,
            rule_repository,
            metric_repository,
            application_config,
        )

    def execute_polling_job(self, task_id: str) -> None:
        """Manually trigger a polling job for a task.

        Does not require any particular state — admins can use this
        to force an immediate poll outside the normal loop cadence.

        Args:
            task_id: ID of the task to poll

        Raises:
            HTTPException: If service not initialized, task not found,
                or task is not a pollable GCP agent
        """
        polling_service = get_global_agent_polling_service()
        if not polling_service:
            raise HTTPException(
                status_code=503,
                detail="Global agent polling service is not initialized.",
            )

        task = self.task_repository.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        if not task.is_agentic:
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} is not available for agent polling",
            )

        if (
            task.task_metadata is None
            or task.task_metadata.creation_source is None
            or not isinstance(
                task.task_metadata.creation_source.root, GCPAgentCreationSource
            )
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} is not a GCP agent. Only GCP agents support polling.",
            )

        job = AgentPollingJob(task_id=task.id)
        enqueued, _ = polling_service.enqueue(job)
        if enqueued:
            logger.info(f"Enqueued manual polling job for task {task_id}")
        else:
            logger.info(f"Polling job for task {task_id} is already active")
