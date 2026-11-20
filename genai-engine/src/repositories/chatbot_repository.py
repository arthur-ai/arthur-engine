import json
import logging
from typing import List, Optional, cast

from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST

from db_models import DatabaseApplicationConfiguration
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.chatbot_schemas import (
    ChatbotConfigResponse,
    ChatbotConfigUpdateRequest,
    ChatbotRequest,
)
from schemas.custom_exceptions import DefaultModelProviderNotSetException
from schemas.enums import ApplicationConfigurations
from services.chatbot.api_call_service import ApiCallService
from services.chatbot.chatbot_prompts import get_api_index
from services.chatbot.chatbot_service import ChatbotService
from services.prompt.chat_completion_service import ChatCompletionService
from utils.constants import (
    ARTHUR_SYSTEM_TASK_ID,
    CHATBOT_PROMPT_NAME,
    CHATBOT_SUMMARIZER_PROMPT_NAME,
)

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

    def _default_model(self) -> tuple[Optional[ModelProvider], Optional[str]]:
        """The instance's default model provider, which the chatbot always uses.
        (None, None) when none is set."""
        try:
            return self.model_provider_repo.resolve_model(None, None)
        except DefaultModelProviderNotSetException:
            return None, None

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

        summarizer_prompt = cast(
            AgenticPrompt,
            self.agentic_prompt_repo.get_llm_item_by_tag(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=CHATBOT_SUMMARIZER_PROMPT_NAME,
                tag="production",
            ),
        )
        # The chatbot and its summarizer always run on the default model provider;
        # the model stored on their prompts is not used.
        chatbot_model_provider, chatbot_model_name = (
            self.model_provider_repo.resolve_model(None, None)
        )
        llm_client = self.model_provider_repo.get_model_provider_client(
            chatbot_model_provider,
        )
        summarizer_prompt = summarizer_prompt.model_copy(
            update={
                "model_provider": chatbot_model_provider.value,
                "model_name": chatbot_model_name,
            },
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
            summarizer_prompt=summarizer_prompt,
        )

        prompt = chatbot_service.build_prompt(
            chatbot_prompt=chatbot_prompt,
            task_id=task_id,
            history=request.history,
            model_provider=chatbot_model_provider,
            model_name=chatbot_model_name,
            blacklist=blacklist,
        )

        return StreamingResponse(
            chatbot_service.safe_stream(
                prompt, llm_client, user_id, request.session_id
            ),
            media_type="text/event-stream",
        )

    def get_chatbot_config(self, app: FastAPI) -> ChatbotConfigResponse:
        model_provider, model_name = self._default_model()
        return ChatbotConfigResponse(
            model_provider=model_provider,
            model_name=model_name,
            blacklist_endpoints=self.get_blacklist_endpoints(),
            available_endpoints=get_api_index(app),
        )

    def update_chatbot_config(
        self,
        update: ChatbotConfigUpdateRequest,
        app: FastAPI,
    ) -> ChatbotConfigResponse:
        if update.model_provider is not None or update.model_name is not None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=(
                    "The chatbot uses the default model provider. Set the model on "
                    "the Model Providers page instead."
                ),
            )
        if update.blacklist_endpoints is not None:
            self.set_blacklist_endpoints(update.blacklist_endpoints)
        return self.get_chatbot_config(app)
