import logging
from uuid import UUID

from arthur_common.models.enums import AgentPollingStatus
from arthur_common.models.request_schemas import AgentMetadata
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models.agent_polling_models import DatabaseAgentPollingData
from schemas.internal_schemas import AgentPollingData
from services.agent_discovery.registered_agent_polling_service import (
    AgentPollingJob,
    get_registered_agent_polling_service,
)

logger = logging.getLogger(__name__)


class AgentDiscoveryRepository:
    def __init__(self, db_session: Session):
        """Initializes repository for basic operations on the agent discovery table"""
        self.db_session = db_session

    def start_polling_for_agent(
        self,
        task_id: str,
        agent_metadata: AgentMetadata,
    ) -> None:
        # Check if polling service is initialized
        polling_service = get_registered_agent_polling_service()
        if not polling_service:
            raise HTTPException(
                status_code=503,
                detail="Registered agent polling service is not initialized. Skipping adding this agent to the polling queue.",
            )

        agent_polling_data = AgentPollingData.from_metadata_request_model(
            task_id,
            agent_metadata,
        )

        db_model = agent_polling_data.to_database_model()
        self.db_session.add(db_model)

        try:
            self.db_session.commit()
        except IntegrityError as e:
            self.db_session.rollback()
            error_msg = str(e.orig)

            # Handle unique constraint violation
            if "uq_gcp_resource_id" in error_msg:
                resource_id = (
                    agent_metadata.gcp_metadata.resource_id
                    if agent_metadata.gcp_metadata
                    else "unknown"
                )
                raise HTTPException(
                    status_code=409,
                    detail=f"Agent with resource_id '{resource_id}' is already registered for polling.",
                )
            # Handle missing gcp_credentials for GCP provider
            elif "ck_gcp_credentials_required" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="GCP provider requires gcp_credentials to be provided.",
                )
            # Handle missing required fields in gcp_credentials
            elif "ck_gcp_credentials_fields" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="GCP credentials must contain 'project_id', 'region', and 'resource_id' fields.",
                )
            # Unknown integrity error
            raise

        # Enqueue the first polling job with a 10-second delay
        job = AgentPollingJob(
            agent_polling_data_id=db_model.id,
            delay_seconds=10,
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

    def retry_agent_polling_job(self, agent_polling_data_id: UUID) -> None:
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
            delay_seconds=10,
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
