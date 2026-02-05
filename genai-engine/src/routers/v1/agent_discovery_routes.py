"""Agent Discovery Routes for GenAI Engine.

This module provides endpoints for discovering agents from infrastructure (e.g., GCP Vertex AI).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette import status

from dependencies import get_application_config, get_db_session
from repositories.agent_discovery_repository import AgentDiscoveryRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agent_discovery_schemas import (
    DiscoverAgentsRequest,
    DiscoverAgentsResponse,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, User
from services.agent_discovery_service import AgentDiscoveryService
from utils.users import permission_checker

agent_discovery_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)

logger = logging.getLogger(__name__)


################################
#### Agent Discovery Routes ####
################################


@agent_discovery_routes.post(
    "/discover-agents",
    description="Discover agents from infrastructure (e.g., GCP Vertex AI). "
    "This endpoint queries the infrastructure provider and Cloud Trace to find deployed agents.",
    response_model=DiscoverAgentsResponse,
    response_model_exclude_none=False,
    tags=["Agent Discovery"],
    status_code=status.HTTP_200_OK,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def discover_agents(
    request: DiscoverAgentsRequest,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> DiscoverAgentsResponse:
    """Discover agents from infrastructure.

    This endpoint:
    1. Validates the data plane exists and is supported (currently GCP only)
    2. Lists deployed agents from the infrastructure (e.g., Vertex AI)
    3. Fetches trace data from Cloud Trace to extract tools and sub-agents
    4. Returns discovered agents with their metadata

    Args:
        request: Discovery request with data_plane_id and lookback_hours
        db_session: Database session (injected)
        application_config: Application configuration (injected)
        current_user: Authenticated user (injected)

    Returns:
        DiscoverAgentsResponse containing discovered agents and metadata

    Raises:
        HTTPException: If discovery fails or data plane is invalid
    """
    try:
        # Initialize discovery service
        service = AgentDiscoveryService(db_session)

        # Perform discovery
        response = service.discover_agents(
            data_plane_id=request.data_plane_id,
            lookback_hours=request.lookback_hours,
        )

        return response

    except ValueError as e:
        # Configuration error (e.g., missing GOOGLE_CLOUD_PROJECT)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        # Unexpected error during discovery
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent discovery failed: {str(e)}",
        )
    finally:
        db_session.close()


@agent_discovery_routes.post(
    "/discover-agents/retry/{agent_polling_data_id}",
    description="Retry a failed agent polling job for a given agent polling data id.",
    tags=["Agent Discovery"],
    status_code=status.HTTP_200_OK,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def retry_agent_polling(
    agent_polling_data_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> JSONResponse:
    """Retry a failed agent polling job for a given agent polling data id"""
    try:
        agent_discovery_repository = AgentDiscoveryRepository(db_session)
        agent_discovery_repository.retry_agent_polling_job(agent_polling_data_id)
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Successfully enqueued retry job for agent {agent_polling_data_id}",
            },
        )
    except HTTPException as e:
        raise
    except Exception as e:
        # Unexpected error during discovery
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent discovery failed: {str(e)}",
        )
