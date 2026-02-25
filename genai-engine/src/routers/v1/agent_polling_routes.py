from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dependencies import get_db_session
from repositories.agent_polling_repository import AgentPollingRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agent_discovery_schemas import (
    DiscoverAndPollResponse,
    ExecutePollingResponse,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from services.task.global_agent_polling_service import get_global_agent_polling_service
from utils.users import permission_checker

agent_polling_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@agent_polling_routes.post(
    "/tasks/{task_id}/agent-polling/execute",
    description="Manually trigger a polling job for a task. "
    "Does not require any particular state — admins can use this "
    "to force an immediate poll outside the normal loop cadence.",
    response_model=ExecutePollingResponse,
    tags=["Agent Discovery"],
    status_code=status.HTTP_200_OK,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def execute_agent_polling(
    task_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ExecutePollingResponse:
    """Manually trigger a polling job for a task."""
    try:
        agent_polling_repository = AgentPollingRepository(db_session)
        agent_polling_repository.execute_polling_job(task_id)
        return ExecutePollingResponse(status="enqueued", task_id=task_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute polling: {str(e)}",
        )


@agent_polling_routes.post(
    "/agent-polling/execute-all",
    description="Manually trigger a full agent discovery and polling cycle. "
    "Discovers new GCP agents and enqueues trace-fetch jobs for all eligible tasks. "
    "Use wait_for_completion=true to block until all polling jobs finish.",
    response_model=DiscoverAndPollResponse,
    tags=["Agent Discovery"],
    status_code=status.HTTP_200_OK,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def execute_all_agent_polling(
    wait_for_completion: bool = False,
    timeout: int | None = None,
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> DiscoverAndPollResponse:
    """Manually trigger a full discovery + polling cycle.

    Args:
        wait_for_completion: If true, block until all polling jobs complete.
                            If false (default), return immediately after enqueuing.
        timeout: Maximum seconds to wait for jobs to complete (only used with wait_for_completion=true).
                Default: None (no timeout)
    """
    polling_service = get_global_agent_polling_service()
    if not polling_service:
        raise HTTPException(
            status_code=503,
            detail="Global agent polling service is not initialized.",
        )

    try:
        return polling_service._discover_and_poll_agents(
            wait_for_completion=wait_for_completion,
            timeout=timeout,
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute polling: {str(e)}",
        )
