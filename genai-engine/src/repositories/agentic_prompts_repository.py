from typing import Type

from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_models.agentic_prompt_models import Base, DatabaseAgenticPrompt
from repositories.base_llm_repository import BaseLLMRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.request_schemas import CompletionRequest, PromptCompletionRequest
from schemas.response_schemas import (
    AgenticPromptRunResponse,
    AgenticPromptVersionListResponse,
    AgenticPromptVersionResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService


class AgenticPromptRepository(BaseLLMRepository):
    db_model: Type[Base] = DatabaseAgenticPrompt
    version_list_response_model: Type[BaseModel] = AgenticPromptVersionListResponse

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.model_provider_repo = ModelProviderRepository(db_session)

    def from_db_model(self, db_prompt: DatabaseAgenticPrompt) -> AgenticPrompt:
        return AgenticPrompt.model_validate(db_prompt.__dict__)

    def to_db_model(self, task_id: str, item: AgenticPrompt) -> DatabaseAgenticPrompt:
        """Convert an AgenticPrompt into a DatabaseAgenticPrompt"""
        return DatabaseAgenticPrompt(
            **item.model_dump(mode="python", exclude_none=True),
            task_id=task_id,
        )

    def _to_versions_reponse_item(self, db_item: Base) -> AgenticPromptVersionResponse:
        num_messages = len(db_item.messages or [])
        num_tools = len(db_item.tools or [])

        return AgenticPromptVersionResponse(
            version=db_item.version,
            created_at=db_item.created_at,
            deleted_at=db_item.deleted_at,
            model_provider=db_item.model_provider,
            model_name=db_item.model_name,
            num_messages=num_messages,
            num_tools=num_tools,
        )

    def _clear_db_item_data(self, db_item: Base) -> None:
        db_item.model_name = ""
        db_item.messages = []
        db_item.tools = None
        db_item.config = None

    def save_llm_item(self, task_id: str, item: AgenticPrompt) -> BaseModel:
        item.variables = list(
            self.chat_completion_service.find_missing_variables_in_messages(
                variable_map={},
                messages=item.messages,
            ),
        )
        return super().save_llm_item(task_id, item)

    async def run_unsaved_prompt(
        self,
        unsaved_prompt: CompletionRequest,
    ) -> AgenticPromptRunResponse:
        llm_client = self.model_provider_repo.get_model_provider_client(
            provider=unsaved_prompt.model_provider,
        )
        prompt, completion_request = ChatCompletionService.to_prompt_and_request(
            unsaved_prompt,
        )
        return await self.chat_completion_service.execute_prompt_completion(
            llm_client,
            prompt,
            completion_request,
        )

    async def run_saved_prompt(
        self,
        task_id: str,
        prompt_name: str,
        prompt_version: str,
        completion_request: PromptCompletionRequest,
    ) -> AgenticPromptRunResponse:
        prompt = self.get_llm_item(
            task_id,
            prompt_name,
            prompt_version,
        )
        llm_client = self.model_provider_repo.get_model_provider_client(
            provider=prompt.model_provider,
        )
        return await self.chat_completion_service.execute_prompt_completion(
            llm_client,
            prompt,
            completion_request,
        )
