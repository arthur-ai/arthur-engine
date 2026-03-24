from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth.authorization_header_elements import (
    get_bearer_access_token_from_cookie_or_header,
)
from dependencies import get_db_session
from repositories.chatbot_repository import ChatbotRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.chatbot_schemas import (
    ChatbotConfigResponse,
    ChatbotConfigUpdateRequest,
    ChatbotRequest,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from utils.constants import GENAI_ENGINE_INGRESS_URI_ENV_VAR
from utils.users import permission_checker
from utils.utils import get_env_var

chatbot_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@chatbot_routes.post(
    "/tasks/{task_id}/chatbot/stream",
    summary="Stream a chatbot response",
    description="Send a message to the Arthur AI chatbot and receive a streaming response. The chatbot can call Arthur Engine API endpoints on your behalf.",
    tags=["Chatbot"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def stream_chatbot(
    request: Request,
    task_id: str,
    body: ChatbotRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    token: str = Depends(get_bearer_access_token_from_cookie_or_header),
) -> StreamingResponse:
    try:
        repo = ChatbotRepository(db_session)

        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        base_url = get_env_var(GENAI_ENGINE_INGRESS_URI_ENV_VAR, none_on_missing=True)
        if not base_url:
            raise HTTPException(
                status_code=400,
                detail="GENAI_ENGINE_INGRESS_URI is not set",
            )

        user_id = current_user.id
        return repo.stream_response(
            body,
            task_id,
            token,
            request.app,
            base_url,
            user_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chatbot_routes.get(
    "/chatbot/config",
    summary="Get chatbot model configuration",
    description="Returns the model provider, model name, blacklisted endpoints, and available endpoints.",
    response_model=ChatbotConfigResponse,
    tags=["Chatbot"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_chatbot_config(
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ChatbotConfigResponse:
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    repo = ChatbotRepository(db_session)
    return repo.get_chatbot_config(request.app)


@chatbot_routes.put(
    "/chatbot/config",
    summary="Update chatbot model configuration",
    description="Saves a new version of the chatbot prompt with the specified model provider and model name, and tags it as production.",
    response_model=ChatbotConfigResponse,
    tags=["Chatbot"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_chatbot_config(
    request: Request,
    body: ChatbotConfigUpdateRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ChatbotConfigResponse:
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    repo = ChatbotRepository(db_session)
    return repo.update_chatbot_config(body, request.app)


@chatbot_routes.delete(
    "/chatbot/history/{conversation_id}",
    summary="Clear chatbot conversation history",
    tags=["Chatbot"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def clear_chatbot_history(
    conversation_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> None:
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = current_user.id
    repo = ChatbotRepository(db_session)
    repo.clear_conversation_history(user_id, conversation_id)
