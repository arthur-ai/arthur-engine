from typing import Union, List

import litellm
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.utils import ModelResponse

from schemas.enums import ModelProvider


def supported_models() -> dict[str, list[str]]:
    models = dict()
    for model_name, cost_config in litellm.model_cost.items():
        # only support chat based models for now
        if cost_config.get("mode") != "chat":
            continue

        provider = cost_config["litellm_provider"]
        if provider not in models:
            models[provider] = []

        # filter out ft models for openai specifically
        if provider == ModelProvider.OPENAI and litellm.is_openai_finetune_model(
            model_name
        ):
            continue

        models[provider].append(model_name)
    return models


SUPPORTED_TEXT_MODELS = supported_models()


class LLMClient:
    def __init__(self, provider: ModelProvider, api_key: str):
        self.provider = provider
        self.api_key = api_key

    def completion(self, *args, **kwargs) -> Union[ModelResponse, CustomStreamWrapper]:
        # Delegate to the top-level function
        return litellm.completion(*args, api_key=self.api_key, **kwargs)

    async def acompletion(
        self, *args, **kwargs
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        # Delegate to the top-level function
        return await litellm.acompletion(*args, api_key=self.api_key, **kwargs)

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
