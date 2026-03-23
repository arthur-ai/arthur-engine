import json
import logging
from typing import List, cast

from fastapi import FastAPI
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from db_models import DatabaseApplicationConfiguration
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.chatbot_schemas import (
    ChatbotConfigResponse,
    ChatbotConfigUpdateRequest,
    ChatbotRequest,
)
from schemas.enums import ApplicationConfigurations
from schemas.request_schemas import CreateAgenticPromptRequest
from services.chatbot.api_call_service import ApiCallService
from services.chatbot.chatbot_prompts import get_api_index
from services.chatbot.chatbot_service import (
    ChatbotService,
    clear_conversation_history,
    get_conversation_history,
)
from services.prompt.chat_completion_service import ChatCompletionService
from utils.constants import ARTHUR_SYSTEM_TASK_ID, CHATBOT_PROMPT_NAME

logger = logging.getLogger(__name__)


class ChatbotRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.model_provider_repo = ModelProviderRepository(db_session)
        self.agentic_prompt_repo = AgenticPromptRepository(db_session)
        self.chat_completion_service = ChatCompletionService()

    def get_blacklist_endpoints(self) -> List[str]:
        row = (
            self.db_session.query(DatabaseApplicationConfiguration)
            .filter_by(
                name=ApplicationConfigurations.CHATBOT_BLACKLIST_ENDPOINTS,
            )
            .first()
        )
        if row is None:
            return []
        result: List[str] = json.loads(row.value)
        return result

    def set_blacklist_endpoints(self, endpoints: List[str]) -> None:
        row = (
            self.db_session.query(DatabaseApplicationConfiguration)
            .filter_by(
                name=ApplicationConfigurations.CHATBOT_BLACKLIST_ENDPOINTS,
            )
            .first()
        )
        value = json.dumps(endpoints)
        if row is None:
            self.db_session.add(
                DatabaseApplicationConfiguration(
                    name=ApplicationConfigurations.CHATBOT_BLACKLIST_ENDPOINTS,
                    value=value,
                ),
            )
        else:
            row.value = value
        self.db_session.commit()

    def stream_response(
        self,
        request: ChatbotRequest,
        task_id: str,
        token: str,
        app: FastAPI,
        base_url: str,
        user_id: str,
    ) -> StreamingResponse:
        chatbot_prompt = cast(
            AgenticPrompt,
            self.agentic_prompt_repo.get_llm_item_by_tag(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=CHATBOT_PROMPT_NAME,
                tag="production",
            ),
        )

        blacklist = self.get_blacklist_endpoints()
        api_call_service = ApiCallService(
            token=token,
            base_url=base_url,
            blacklist=blacklist,
        )
        chatbot_service = ChatbotService(
            chat_completion_service=self.chat_completion_service,
            api_call_service=api_call_service,
            api_index=get_api_index(app, blacklist=blacklist),
            db_session=self.db_session,
        )

        history = get_conversation_history(user_id, request.conversation_id)

        llm_client = self.model_provider_repo.get_model_provider_client(
            chatbot_prompt.model_provider,
        )

        prompt = chatbot_service.build_prompt(
            chatbot_prompt=chatbot_prompt,
            task_id=task_id,
            history=history,
            user_message=request.message,
            model_provider=chatbot_prompt.model_provider,
            model_name=chatbot_prompt.model_name,
            blacklist=blacklist,
        )

        return StreamingResponse(
            chatbot_service.stream(
                prompt,
                llm_client,
                user_id,
                request.conversation_id,
            ),
            media_type="text/event-stream",
        )

    def get_chatbot_config(self, app: FastAPI) -> ChatbotConfigResponse:
        chatbot_prompt = cast(
            AgenticPrompt,
            self.agentic_prompt_repo.get_llm_item_by_tag(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=CHATBOT_PROMPT_NAME,
                tag="production",
            ),
        )
        blacklist = self.get_blacklist_endpoints()
        available = get_api_index(app)
        return ChatbotConfigResponse(
            model_provider=chatbot_prompt.model_provider,
            model_name=chatbot_prompt.model_name,
            blacklist_endpoints=blacklist,
            available_endpoints=available,
        )

    def update_chatbot_config(
        self,
        update: ChatbotConfigUpdateRequest,
    ) -> ChatbotConfigResponse:
        chatbot_prompt = cast(
            AgenticPrompt,
            self.agentic_prompt_repo.get_llm_item_by_tag(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=CHATBOT_PROMPT_NAME,
                tag="production",
            ),
        )

        model_provider = update.model_provider or chatbot_prompt.model_provider
        model_name = update.model_name or chatbot_prompt.model_name

        if (
            chatbot_prompt.model_provider == model_provider
            and chatbot_prompt.model_name == model_name
        ):
            logger.info(
                f"Chatbot model and provider are the same, skipping prompt update",
            )
        else:
            new_version = self.agentic_prompt_repo.save_llm_item(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=CHATBOT_PROMPT_NAME,
                item=CreateAgenticPromptRequest(
                    messages=chatbot_prompt.messages,
                    model_name=model_name,
                    model_provider=model_provider,
                    tools=chatbot_prompt.tools,
                    config=chatbot_prompt.config,  # type: ignore[arg-type]
                ),
            )

            self.agentic_prompt_repo.add_tag_to_llm_item_version(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=CHATBOT_PROMPT_NAME,
                item_version=str(new_version.version),
                tag="production",
            )

        if update.blacklist_endpoints is not None:
            self.set_blacklist_endpoints(update.blacklist_endpoints)

        return ChatbotConfigResponse(
            model_provider=model_provider,
            model_name=model_name,
            blacklist_endpoints=self.get_blacklist_endpoints(),
        )

    def clear_conversation_history(
        self,
        user_id: str,
        conversation_id: str,
    ) -> None:
        clear_conversation_history(user_id, conversation_id)
