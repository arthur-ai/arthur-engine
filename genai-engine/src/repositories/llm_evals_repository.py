from typing import Type

from pydantic import BaseModel

from db_models.llm_eval_models import Base, DatabaseLLMEval
from repositories.base_llm_repository import BaseLLMRepository
from schemas.llm_eval_schemas import LLMEval
from schemas.response_schemas import (
    LLMEvalsVersionListResponse,
    LLMVersionResponse,
)


class LLMEvalsRepository(BaseLLMRepository):
    db_model: Type[Base] = DatabaseLLMEval
    version_list_response_model: Type[BaseModel] = LLMEvalsVersionListResponse

    def _from_db_model(self, db_item: Base) -> BaseModel:
        return LLMEval.from_db_model(db_item)

    def _to_versions_reponse_item(self, db_item: Base) -> LLMVersionResponse:
        return LLMVersionResponse(
            version=db_item.version,
            created_at=db_item.created_at,
            deleted_at=db_item.deleted_at,
            model_provider=db_item.model_provider,
            model_name=db_item.model_name,
        )

    def _clear_db_item_data(self, db_item: Base) -> None:
        db_item.model_name = ""
        db_item.instructions = ""
        db_item.min_score = 0
        db_item.max_score = 1
        db_item.config = None
