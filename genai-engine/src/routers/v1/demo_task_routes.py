import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.config import Config
from dependencies import get_application_config, get_db_session
from repositories.demo_task_repository import DemoTaskRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.chatbot_schemas import ChatbotRequest
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, User
from utils.users import enforce_org_scope, permission_checker

logger = logging.getLogger(__name__)

demo_task_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@demo_task_routes.post(
    "/tasks/{task_id}/demos/chatbot/stream",
    description="Stream a demo chatbot response.",
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
@enforce_org_scope()
async def stream_demo_chatbot(
    task_id: str,
    chatbot_request: ChatbotRequest,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> StreamingResponse:
    if not Config.demo_mode():
        raise HTTPException(
            status_code=400,
            detail="Demo mode is not enabled",
        )

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user required",
        )

    try:
        tasks_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        task = tasks_repo.get_task_by_id(task_id)

        demo_task_repo = DemoTaskRepository(db_session)
        return demo_task_repo.stream_response(
            task_id,
            chatbot_request.history,
            current_user.id,
            task.org_id,
            chatbot_request.session_id,
        )
    except ValueError as e:
        logger.warning("Demo chatbot stream rejected: %s", e)
        raise HTTPException(
            status_code=400,
            detail="Invalid demo chatbot request.",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Demo chatbot stream failed unexpectedly")
        raise HTTPException(
            status_code=500,
            detail="Failed to stream demo chatbot response.",
        ) from e
