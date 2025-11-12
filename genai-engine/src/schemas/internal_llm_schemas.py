from typing import Optional, Type, Union

from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.utils import ModelResponse
from pydantic import BaseModel, ConfigDict, Field


class LLMModelResponse(BaseModel):
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
