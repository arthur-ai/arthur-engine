from typing import Tuple

from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from clients.llm.llm_client import LLMClient
from repositories.model_provider_repository import ModelProviderRepository
from schemas.chatbot_schemas import ChatbotRequest
from services.chatbot.api_call_service import ApiCallService
from services.chatbot.chatbot_prompts import SYSTEM_PROMPT, get_api_index
from services.chatbot.chatbot_service import (
    ChatbotService,
    get_conversation_history,
)
from services.prompt.chat_completion_service import ChatCompletionService

PROVIDER_PRIORITY = [
    (ModelProvider.ANTHROPIC, "claude-sonnet-4-6"),
    (ModelProvider.OPENAI, "gpt-4.1"),
    (ModelProvider.GEMINI, "gemini-3-flash-preview"),
]


class ChatbotRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.model_provider_repo = ModelProviderRepository(db_session)
        self.chat_completion_service = ChatCompletionService()

    def get_provider_and_client(self) -> Tuple[ModelProvider, str, LLMClient]:
        configured = {
            p.provider
            for p in self.model_provider_repo.list_model_providers()
            if p.enabled
        }
        for provider, model_name in PROVIDER_PRIORITY:
            if provider in configured:
                return (
                    provider,
                    model_name,
                    self.model_provider_repo.get_model_provider_client(provider),
                )
        raise HTTPException(
            status_code=503,
            detail="Chatbot requires Anthropic, OpenAI, or Gemini to be configured as a model provider.",
        )

    def stream_response(
        self,
        request: ChatbotRequest,
        task_id: str,
        token: str,
        app: FastAPI,
        base_url: str,
        user_id: str,
    ) -> StreamingResponse:
        provider, model_name, llm_client = self.get_provider_and_client()
        api_call_service = ApiCallService(token=token, base_url=base_url)
        chatbot_service = ChatbotService(
            chat_completion_service=self.chat_completion_service,
            api_call_service=api_call_service,
            api_index=get_api_index(app),
        )

        history = get_conversation_history(user_id, request.conversation_id)

        prompt = chatbot_service.build_prompt(
            system_prompt=SYSTEM_PROMPT,
            task_id=task_id,
            history=history,
            user_message=request.message,
            model_provider=provider,
            model_name=model_name,
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
