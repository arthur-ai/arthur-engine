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
from schemas.chatbot_schemas import ChatbotRequest
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from services.chatbot.chatbot_service import clear_conversation_history
from utils.users import permission_checker

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
        user_id = current_user.id if current_user else "anonymous"
        return repo.stream_response(
            body,
            task_id,
            token,
            request.app,
            str(request.base_url).rstrip("/"),
            user_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chatbot_routes.delete(
    "/chatbot/history/{conversation_id}",
    summary="Clear chatbot conversation history",
    tags=["Chatbot"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def clear_chatbot_history(
    conversation_id: str,
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> None:
    user_id = current_user.id if current_user else "anonymous"
    clear_conversation_history(user_id, conversation_id)
