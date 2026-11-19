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
from schemas.request_schemas import CreateAgenticPromptRequest
from services.chatbot.api_call_service import ApiCallService
from services.chatbot.chatbot_prompts import get_api_index
from services.chatbot.chatbot_service import ChatbotService
from services.prompt.chat_completion_service import ChatCompletionService
from utils.constants import (
    ARTHUR_SYSTEM_TASK_ID,
    CHATBOT_PROMPT_NAME,
    CHATBOT_SUMMARIZER_PROMPT_NAME,
    EMPTY_MODEL_NAME,
    EMPTY_MODEL_PROVIDER,
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

    def _resolve_chatbot_model(
        self,
        chatbot_prompt: AgenticPrompt,
    ) -> tuple[Optional[ModelProvider], Optional[str]]:
        """The chatbot's model, with the 'empty' placeholder resolved to the default
        model provider. (None, None) when it uses the default and none is set."""
        try:
            return self.model_provider_repo.resolve_model(
                chatbot_prompt.model_provider,
                chatbot_prompt.model_name,
            )
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
        chatbot_model_provider, chatbot_model_name = (
            self.model_provider_repo.resolve_model(
                chatbot_prompt.model_provider,
                chatbot_prompt.model_name,
            )
        )
        llm_client = self.model_provider_repo.get_model_provider_client(
            chatbot_model_provider,
        )
        if summarizer_prompt.model_provider == EMPTY_MODEL_PROVIDER:
            # The summarizer runs on the chatbot's client, so it follows the
            # chatbot's model when it uses the default.
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
        model_provider, model_name = self._resolve_chatbot_model(chatbot_prompt)
        return ChatbotConfigResponse(
            model_provider=model_provider,
            model_name=model_name,
            uses_default_model=chatbot_prompt.model_provider == EMPTY_MODEL_PROVIDER,
            blacklist_endpoints=blacklist,
            available_endpoints=available,
        )

    def _save_chatbot_prompts(self, model_provider: str, model_name: str) -> None:
        """Save a new production version of both chatbot prompts on the given model.
        The 'empty' placeholder makes them follow the default model provider."""
        for prompt_name in (CHATBOT_PROMPT_NAME, CHATBOT_SUMMARIZER_PROMPT_NAME):
            prompt = cast(
                AgenticPrompt,
                self.agentic_prompt_repo.get_llm_item_by_tag(
                    task_id=ARTHUR_SYSTEM_TASK_ID,
                    item_name=prompt_name,
                    tag="production",
                ),
            )
            item = CreateAgenticPromptRequest(
                messages=prompt.messages,
                model_name=model_name,
                # Placeholder provider: the request type only accepts real providers,
                # so the actual one (possibly 'empty') is set below.
                model_provider=ModelProvider.OPENAI,
                tools=prompt.tools,
                config=prompt.config,  # type: ignore[arg-type]
            ).model_copy(update={"model_provider": model_provider})
            new_version = self.agentic_prompt_repo.save_llm_item(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=prompt_name,
                item=item,
            )
            self.agentic_prompt_repo.add_tag_to_llm_item_version(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=prompt_name,
                item_version=str(new_version.version),
                tag="production",
            )

    def update_chatbot_config(
        self,
        update: ChatbotConfigUpdateRequest,
        app: FastAPI,
    ) -> ChatbotConfigResponse:
        chatbot_prompt = cast(
            AgenticPrompt,
            self.agentic_prompt_repo.get_llm_item_by_tag(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=CHATBOT_PROMPT_NAME,
                tag="production",
            ),
        )

        current_provider, current_model = self._resolve_chatbot_model(chatbot_prompt)
        uses_default_model = chatbot_prompt.model_provider == EMPTY_MODEL_PROVIDER
        model_provider = update.model_provider or current_provider
        model_name = update.model_name or current_model

        if update.use_default_model:
            if uses_default_model:
                logger.info(
                    "Chatbot already uses the default model, skipping prompt update"
                )
            else:
                self._save_chatbot_prompts(EMPTY_MODEL_PROVIDER, EMPTY_MODEL_NAME)
                uses_default_model = True
                model_provider, model_name = self._resolve_chatbot_model(
                    chatbot_prompt.model_copy(
                        update={
                            "model_provider": EMPTY_MODEL_PROVIDER,
                            "model_name": EMPTY_MODEL_NAME,
                        },
                    ),
                )
        elif update.model_provider is None and update.model_name is None:
            logger.info("No chatbot model change requested, skipping prompt update")
        elif model_provider is None or model_name is None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=(
                    "Set both model_provider and model_name: the chatbot uses the "
                    "default model provider, and none is set."
                ),
            )
        elif uses_default_model and (model_provider, model_name) == (
            current_provider,
            current_model,
        ):
            # A client that sends the whole form back sends the default's model too;
            # that is not a pick, so the chatbot keeps following the default.
            logger.info(
                "Requested model is the current default, chatbot keeps using the default",
            )
        elif (
            chatbot_prompt.model_provider == model_provider
            and chatbot_prompt.model_name == model_name
        ):
            logger.info(
                f"Chatbot model and provider are the same, skipping prompt update",
            )
        else:
            uses_default_model = False
            self._save_chatbot_prompts(ModelProvider(model_provider).value, model_name)

        if update.blacklist_endpoints is not None:
            self.set_blacklist_endpoints(update.blacklist_endpoints)

        return ChatbotConfigResponse(
            model_provider=model_provider,
            model_name=model_name,
            uses_default_model=uses_default_model,
            blacklist_endpoints=self.get_blacklist_endpoints(),
            available_endpoints=get_api_index(app),
        )
