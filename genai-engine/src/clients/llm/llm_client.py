import logging
import threading
import time
from typing import Any, List, Optional, Type, Union

import litellm
from litellm import completion_cost, get_model_cost_map, model_cost_map_url
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.utils import ModelResponse
from pydantic import BaseModel, ConfigDict, Field

from schemas.enums import ModelProvider

logger = logging.getLogger(__name__)


class LLMModelResponse(BaseModel):
    # NOTE: We use arbitrary_types_allowed=True here to allow the response parameter to be the non-pydantic types ModelResponse/CustomStreamWrapper
    model_config = ConfigDict(arbitrary_types_allowed=True)

    response: Union[ModelResponse, CustomStreamWrapper] = Field(
        ...,
        description="The raw response from litellm",
    )
    structured_output_response: Optional[Type[BaseModel]] = Field(
        None,
        description="The structured output base model response from the model",
    )
    cost: Optional[float] = Field(None, description="The cost of the model response")


def supported_models() -> dict[str, list[str]]:
    models: dict[str, list[str]] = {}
    for model_name, cost_config in get_model_cost_map(url=model_cost_map_url).items():
        # only support chat based models for now
        if cost_config.get("mode") != "chat":
            continue

        # filter out ft models for openai, they aren't usable
        provider = cost_config["litellm_provider"]
        if provider == ModelProvider.OPENAI and litellm.is_openai_finetune_model(
            model_name,
        ):
            continue

        if provider not in models:
            models[provider] = []
        models[provider].append(model_name)
    return models


SUPPORTED_TEXT_MODELS = supported_models()


def refresh_models_periodically() -> None:
    global SUPPORTED_TEXT_MODELS
    while True:
        try:
            time.sleep(8 * 60 * 60)  # 8 hours in seconds
            SUPPORTED_TEXT_MODELS = supported_models()
            logger.info("Refreshed model list")
        except Exception as e:
            logger.warning(f"Failed to refresh model list {str(e)}")


# Start background thread to refresh models
refresh_thread = threading.Thread(target=refresh_models_periodically, daemon=True)
refresh_thread.start()


class LLMClient:
    def __init__(self, provider: ModelProvider, api_key: str):
        self.provider = provider
        self.api_key = api_key

    def completion(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> LLMModelResponse:
        # Delegate to the top-level function
        response = litellm.completion(*args, api_key=self.api_key, **kwargs)
        cost = completion_cost(response)

        llm_model_response = LLMModelResponse(response=response, cost=cost)

        if (
            "response_format" in kwargs
            and isinstance(kwargs["response_format"], type)
            and issubclass(kwargs["response_format"], BaseModel)
            and response.choices[0].message.get("content") is not None
        ):
            llm_model_response.structured_output_response = kwargs[
                "response_format"
            ].model_validate_json(response.choices[0].message.get("content"))

        return llm_model_response

    async def acompletion(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ModelResponse | CustomStreamWrapper:
        # Delegate to the top-level function
        response: ModelResponse | CustomStreamWrapper = await litellm.acompletion(
            *args,
            api_key=self.api_key,
            **kwargs,
        )
        return response

    def get_available_models(self) -> List[str]:
        if self.provider in SUPPORTED_TEXT_MODELS:
            return SUPPORTED_TEXT_MODELS[self.provider]

        # if provider isn't in the pre-configured set of liteLLM cost
        # fallback to fetching from provider's API
        # this may return models the provider supports that are not text models
        # currently, there is no way to filter
        return litellm.get_valid_models(
            api_key=self.api_key,
            check_provider_endpoint=True,
            custom_llm_provider=self.provider,
        )
