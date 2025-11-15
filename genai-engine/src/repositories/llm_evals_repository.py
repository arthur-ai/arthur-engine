from typing import Optional, Type, Union

from litellm import supports_response_schema
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_models.llm_eval_models import Base, DatabaseLLMEval
from repositories.base_llm_repository import BaseLLMRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.llm_eval_schemas import LLMEval, ReasonedScore
from schemas.llm_schemas import LLMConfigSettings, LLMResponseFormat
from schemas.request_schemas import (
    BaseCompletionRequest,
    PromptCompletionRequest,
)
from schemas.response_schemas import (
    LLMEvalRunResponse,
    LLMEvalsVersionListResponse,
    LLMVersionResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService


class LLMEvalsRepository(BaseLLMRepository):
    db_model: Type[Base] = DatabaseLLMEval
    version_list_response_model: Type[BaseModel] = LLMEvalsVersionListResponse

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.model_provider_repo = ModelProviderRepository(db_session)
        self.chat_completion_service = ChatCompletionService()

    def from_db_model(self, db_eval: DatabaseLLMEval) -> LLMEval:
        return LLMEval.model_validate(db_eval.__dict__)

    def to_db_model(self, task_id: str, item: LLMEval) -> DatabaseLLMEval:
        return DatabaseLLMEval(
            task_id=task_id,
            **item.model_dump(mode="python", exclude_none=True),
        )

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
        db_item.config = None

    def from_llm_eval_to_agentic_prompt(
        self,
        llm_eval: LLMEval,
        response_format: Optional[Union[LLMResponseFormat, Type[BaseModel]]] = None,
    ) -> AgenticPrompt:
        messages = [
            {"role": "system", "content": llm_eval.instructions},
        ]

        config_dict = {}
        if llm_eval.config:
            config_dict = llm_eval.config.model_dump(exclude_none=True)

        if response_format is not None:
            config_dict["response_format"] = response_format

        return AgenticPrompt(
            name=llm_eval.name,
            model_name=llm_eval.model_name,
            model_provider=llm_eval.model_provider,
            messages=messages,
            version=llm_eval.version,
            created_at=llm_eval.created_at,
            deleted_at=llm_eval.deleted_at,
            config=LLMConfigSettings(**config_dict),
        )

    def save_llm_item(self, task_id: str, item: LLMEval) -> LLMEval:
        item.variables = list(
            self.chat_completion_service.find_undeclared_variables_in_text(
                item.instructions,
            ),
        )
        return super().save_llm_item(task_id, item)

    def run_llm_eval(
        self,
        task_id: str,
        eval_name: str,
        version: str = "latest",
        completion_request: Optional[BaseCompletionRequest] = None,
    ) -> LLMEvalRunResponse:
        if not self.model_provider_repo:
            raise ValueError("Model provider repository not initialized")

        # get the llm eval
        llm_eval = self.get_llm_item(task_id, eval_name, version)

        if llm_eval.deleted_at is not None:
            raise ValueError(
                f"Cannot run this llm eval because it was deleted on: {llm_eval.deleted_at}",
            )

        # get the llm client
        llm_client = self.model_provider_repo.get_model_provider_client(
            provider=llm_eval.model_provider,
        )

        # NOTE: We currently don't set litellm.enable_json_schema_validation=True, which has litellm validate schemas for models that support structured outputs
        # Some vertex ai models return true for the function below, but don't do any schema validations: https://docs.litellm.ai/docs/completion/json_mode?#validate-json-schema
        # If we choose to support vertex ai in the future, we should set the above flag to True to have litellm validate the schema
        if not supports_response_schema(
            model=llm_eval.model_name,
            custom_llm_provider=llm_eval.model_provider,
        ):
            raise ValueError(
                f"Model {llm_eval.model_name} with provider {llm_eval.model_provider} does not support structured outputs",
            )

        variables = []
        if completion_request and completion_request.variables:
            variables = completion_request.variables

        # create the full completion request
        prompt_completion_request = PromptCompletionRequest(
            variables=variables,
            stream=False,
            strict=True,
        )

        # run the chat completion
        agentic_prompt = self.from_llm_eval_to_agentic_prompt(
            llm_eval=llm_eval,
            response_format=ReasonedScore,
        )

        llm_model_response = (
            self.chat_completion_service.run_chat_completion_raw_response(
                agentic_prompt,
                llm_client,
                prompt_completion_request,
            )
        )

        if llm_model_response.structured_output_response is None:
            raise ValueError(
                f"No structured output response from model {llm_eval.model_name} with provider {llm_eval.model_provider}",
            )

        if not isinstance(
            llm_model_response.structured_output_response,
            ReasonedScore,
        ):
            raise TypeError("Structured output is not a ReasonedScore instance")

        return LLMEvalRunResponse(
            reason=llm_model_response.structured_output_response.reason,
            score=llm_model_response.structured_output_response.score,
            cost=f"{llm_model_response.cost:.6f}",
        )
