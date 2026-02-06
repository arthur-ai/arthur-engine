from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from dependencies import get_db_session
from repositories.agent_polling_repository import AgentPollingRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from utils.users import permission_checker

agent_polling_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@agent_polling_routes.post(
    "/tasks/{task_id}/agent-polling/retry/{agent_polling_data_id}",
    description="Retry a failed agent polling job for a given agent polling data id.",
    tags=["Agent Discovery"],
    status_code=status.HTTP_200_OK,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def retry_agent_polling(
    task_id: str,
    agent_polling_data_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> JSONResponse:
    """Retry a failed agent polling job for a given agent polling data id"""
    try:
        agent_polling_repository = AgentPollingRepository(db_session)
        agent_polling_repository.retry_agent_polling_job(task_id, agent_polling_data_id)
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
