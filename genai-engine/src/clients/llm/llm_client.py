from typing import Union

import litellm
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.utils import ModelResponse

from schemas.enums import ModelProvider


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
