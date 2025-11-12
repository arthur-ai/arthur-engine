from typing import Type

from pydantic import BaseModel

from db_models.agentic_prompt_models import Base, DatabaseAgenticPrompt
from repositories.base_llm_repository import BaseLLMRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.response_schemas import (
    AgenticPromptVersionListResponse,
    AgenticPromptVersionResponse,
)


class AgenticPromptRepository(BaseLLMRepository):
    db_model: Type[Base] = DatabaseAgenticPrompt
    version_list_response_model: Type[BaseModel] = AgenticPromptVersionListResponse

    def _from_db_model(self, db_item: Base) -> BaseModel:
        return AgenticPrompt.from_db_model(db_item)

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
