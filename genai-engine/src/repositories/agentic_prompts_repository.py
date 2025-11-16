from typing import List, Type

from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_models import Base
from db_models.agentic_prompt_models import (
    DatabaseAgenticPrompt,
    DatabaseAgenticPromptVersionTag,
)
from repositories.base_llm_repository import BaseLLMRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.request_schemas import (
    CompletionRequest,
    CreateAgenticPromptRequest,
    PromptCompletionRequest,
)
from schemas.response_schemas import (
    AgenticPromptRunResponse,
    AgenticPromptVersionListResponse,
    AgenticPromptVersionResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService


class AgenticPromptRepository(BaseLLMRepository):
    db_model: Type[Base] = DatabaseAgenticPrompt
    tag_db_model: Type[Base] = DatabaseAgenticPromptVersionTag
    version_list_response_model: Type[BaseModel] = AgenticPromptVersionListResponse

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.model_provider_repo = ModelProviderRepository(db_session)

    def from_db_model(self, db_prompt: DatabaseAgenticPrompt) -> AgenticPrompt:
        return AgenticPrompt(
            name=db_prompt.name,
            messages=db_prompt.messages,
            model_name=db_prompt.model_name,
            model_provider=db_prompt.model_provider,
            version=db_prompt.version,
            tools=db_prompt.tools,
            variables=db_prompt.variables,
            tags=[t.tag for t in db_prompt.version_tags],
            config=db_prompt.config,
            created_at=db_prompt.created_at,
            deleted_at=db_prompt.deleted_at,
        )

    def _extract_variables_from_item(
        self,
        item: CreateAgenticPromptRequest,
    ) -> List[str]:
        return list(
            self.chat_completion_service.find_missing_variables_in_messages(
                variable_map={},
                messages=item.messages,
            ),
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

    def save_llm_item(
        self,
        task_id: str,
        item_name: str,
        item: CreateAgenticPromptRequest,
    ) -> AgenticPrompt:
        return super().save_llm_item(task_id, item_name, item)

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
