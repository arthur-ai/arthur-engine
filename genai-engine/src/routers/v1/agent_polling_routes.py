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
    "/tasks/{task_id}/agent-polling/execute",
    description="Manually trigger a polling job for a task. "
    "Does not require any particular state — admins can use this "
    "to force an immediate poll outside the normal loop cadence.",
    tags=["Agent Discovery"],
    status_code=status.HTTP_200_OK,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def execute_agent_polling(
    task_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> JSONResponse:
    """Manually trigger a polling job for a task."""
    try:
        agent_polling_repository = AgentPollingRepository(db_session)
        agent_polling_repository.execute_polling_job(task_id)
        return JSONResponse(
            status_code=200,
            content={
                "status": "enqueued",
                "task_id": task_id,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute polling: {str(e)}",
        )
