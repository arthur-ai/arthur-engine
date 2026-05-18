from arthur_common.models.request_schemas import NewTaskRequest
from arthur_common.models.response_schemas import TaskResponse
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from clients.telemetry.telemetry_client import TelemetryEventTypes, send_telemetry_event
from config.config import Config
from dependencies import get_application_config, get_db_session
from repositories.demo_task_repository import DemoTaskRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, Task, User
from schemas.request_schemas import DemoTaskChatbotRequest
from services.chatbot.demo_chatbot_service import clear_demo_conversation_history
from utils.users import permission_checker

demo_task_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@demo_task_routes.post(
    "/tasks/demos",
    description="Create a new demo task.",
    response_model=TaskResponse,
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_demo_task(
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TaskResponse:
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

    rules_repo = RuleRepository(db_session)
    tasks_repo = TaskRepository(
        db_session,
        rules_repo,
        MetricRepository(db_session),
        application_config,
    )

    send_telemetry_event(TelemetryEventTypes.TASK_CREATE_INITIATED)
    demo_task_request = NewTaskRequest(
        name="Demo Task",
        is_agentic=True,
    )
    task = tasks_repo.create_task(Task._from_request_model(demo_task_request))
    send_telemetry_event(TelemetryEventTypes.TASK_CREATE_COMPLETED)

    try:
        demo_task_repo = DemoTaskRepository(db_session)
        demo_task_repo.create_demo_items_for_task(task.id, current_user.id)

        return task._to_response_model()
    except ValueError as e:
        tasks_repo.archive_task(task.id)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create demo task: {e}",
        )
    except HTTPException as e:
        tasks_repo.archive_task(task.id)
        raise e
    except Exception as e:
        tasks_repo.archive_task(task.id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create demo task: {e}",
        )


@demo_task_routes.post(
    "/tasks/{task_id}/demos/chatbot/stream",
    description="Stream a demo chatbot response.",
    tags=["Tasks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def stream_demo_chatbot(
    task_id: str,
    demo_task_chatbot_request: DemoTaskChatbotRequest,
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
            demo_task_chatbot_request.user_message,
            current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to stream demo chatbot response: {e}",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stream demo chatbot response: {e}",
        )


@demo_task_routes.delete(
    "/tasks/{task_id}/demos/chatbot/history",
    summary="Clear demo chatbot conversation history",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Demo chatbot conversation history cleared.",
        },
    },
    tags=["Chatbot"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def clear_demo_chatbot_history(
    task_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> None:
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

        # verify task exists
        tasks_repo.get_task_by_id(task_id)

        clear_demo_conversation_history(task_id, current_user.id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear demo chatbot conversation history: {e}",
        )
