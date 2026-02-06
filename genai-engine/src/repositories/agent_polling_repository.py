import logging
from uuid import UUID

from arthur_common.models.enums import AgentPollingStatus
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models.agent_polling_models import DatabaseAgentPollingData
from repositories.configuration_repository import ConfigurationRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.internal_schemas import AgentPollingData
from services.task.registered_agent_polling_service import (
    AgentPollingJob,
    get_registered_agent_polling_service,
)

logger = logging.getLogger(__name__)


class AgentPollingRepository:
    def __init__(self, db_session: Session):
        """Initializes repository for basic operations on the agent discovery table"""
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

    def start_polling_for_agent(
        self,
        task_id: str,
    ) -> None:
        # Check if polling service is initialized
        polling_service = get_registered_agent_polling_service()
        if not polling_service:
            raise HTTPException(
                status_code=503,
                detail="Registered agent polling service is not initialized. Skipping adding this agent to the polling queue.",
            )

        task = self.task_repository.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        if task.is_agentic == False or task.task_metadata is None:
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} is not available for agent polling",
            )

        agent_polling_data = AgentPollingData.from_task_id(
            task_id,
        )

        db_model = agent_polling_data.to_database_model()
        self.db_session.add(db_model)

        try:
            self.db_session.commit()
        except IntegrityError as e:
            self.db_session.rollback()

            # Unknown integrity error
            raise

        # Enqueue the first polling job
        job = AgentPollingJob(
            agent_polling_data_id=db_model.id,
        )
        if polling_service.enqueue(job):
            logger.info(f"Enqueued initial polling job for agent {db_model.id}")
        else:
            # Failed to enqueue - update status to ERROR
            db_model.status = AgentPollingStatus.ERROR.value
            db_model.error_message = (
                "Failed to enqueue initial polling job - job already active"
            )
            self.db_session.commit()
            logger.error(
                f"Failed to enqueue initial polling job for agent {db_model.id}",
            )

    def retry_agent_polling_job(
        self,
        task_id: str,
        agent_polling_data_id: UUID,
    ) -> None:
        """Retry a failed agent polling job for a given agent polling data id"""
        # Check if polling service is initialized
        polling_service = get_registered_agent_polling_service()
        if not polling_service:
            raise HTTPException(
                status_code=503,
                detail="Registered agent polling service is not initialized. Skipping adding this agent to the polling queue.",
            )

        db_agent_polling_data = (
            self.db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data_id)
            .first()
        )
        if not db_agent_polling_data:
            raise HTTPException(
                status_code=404,
                detail=f"Agent polling data {agent_polling_data_id} not found",
            )

        if db_agent_polling_data.task_id != task_id:
            raise HTTPException(
                status_code=400,
                detail=f"Agent polling data {agent_polling_data_id} does not belong to task {task_id}",
            )

        task = self.task_repository.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found",
            )

        if task.is_agentic == False or task.task_metadata is None:
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} is not available for agent polling",
            )

        if db_agent_polling_data.status != AgentPollingStatus.ERROR.value:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry a polling job that is not in an error state",
            )

        db_agent_polling_data.status = AgentPollingStatus.IDLE.value
        db_agent_polling_data.error_message = None
        db_agent_polling_data.failed_runs = 0

        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data_id,
        )
        if polling_service.enqueue(job):
            logger.info(f"Enqueued retry polling job for agent {agent_polling_data_id}")
            self.db_session.commit()
        else:
            # Failed to enqueue - update status to ERROR
            db_agent_polling_data.status = AgentPollingStatus.ERROR.value
            db_agent_polling_data.error_message = "Failed to enqueue retry polling job"
            logger.error(
                f"Failed to enqueue retry polling job for agent {agent_polling_data_id}",
            )
            self.db_session.commit()
            raise HTTPException(
                status_code=503,
                detail="Registered agent polling service is not initialized. Skipping adding this agent to the polling queue.",
            )
