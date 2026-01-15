import logging
import os
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

# LiteLLM debug logging configuration
# Enable debug logging when LITELLM_LOG=DEBUG environment variable is set
# This uses litellm._turn_on_debug() as recommended by LiteLLM for detailed error debugging
if os.getenv("LITELLM_LOG") == "DEBUG":
    try:
        # Use the recommended method for detailed debugging
        litellm._turn_on_debug()
        logger.info(
            "LiteLLM debug logging enabled via LITELLM_LOG=DEBUG (using _turn_on_debug())",
        )
    except (AttributeError, TypeError):
        # Fallback to set_verbose if _turn_on_debug is not available
        litellm.set_verbose = True
        logger.info(
            "LiteLLM debug logging enabled via LITELLM_LOG=DEBUG (using set_verbose=True)",
        )


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
    cost: Optional[str] = Field(None, description="The cost of the model response")


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
    def __init__(
        self,
        provider: ModelProvider,
        api_key: str = "",
        project_id: str | None = None,
        region: str | None = None,
    ):
        self.provider = provider
        self.api_key = api_key
        self.project_id = project_id
        self.region = region

    def _get_litellm_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        """Get the appropriate kwargs for litellm based on provider type"""
        litellm_kwargs = kwargs.copy()

        if self.provider == ModelProvider.VERTEX_AI:
            # For Vertex AI, pass vertex_project and vertex_location instead of api_key
            if self.project_id:
                litellm_kwargs["vertex_project"] = self.project_id
            if self.region:
                litellm_kwargs["vertex_location"] = self.region
            # Don't pass api_key for Vertex AI (uses ADC)

            # Enable JSON schema validation for Vertex AI when using structured outputs
            # Vertex AI models claim to support schema validation but don't actually validate it
            # so litellm needs to handle the validation
            if "response_format" in kwargs:
                litellm_kwargs["enable_json_schema_validation"] = True

            # Log Vertex AI configuration for debugging (when debug is enabled)
            if os.getenv("LITELLM_LOG") == "DEBUG":
                logger.debug(
                    f"Vertex AI configuration: project={self.project_id}, region={self.region}, "
                    f"vertex_project={litellm_kwargs.get('vertex_project')}, "
                    f"vertex_location={litellm_kwargs.get('vertex_location')}",
                )
        elif self.provider == ModelProvider.GEMINI:
            # For Gemini, pass api_key - LiteLLM will use it for gemini/* models
            # Alternatively, LiteLLM can use GEMINI_API_KEY environment variable
            if self.api_key:
                litellm_kwargs["api_key"] = self.api_key
            # Log Gemini configuration for debugging
            if os.getenv("LITELLM_LOG") == "DEBUG":
                logger.debug(
                    f"Gemini configuration: api_key={'***' + self.api_key[-4:] if len(self.api_key) > 4 else '***' if self.api_key else 'NOT SET'}",
                )
        else:
            # For other providers (Anthropic, OpenAI), use api_key
            if self.api_key:
                litellm_kwargs["api_key"] = self.api_key

        return litellm_kwargs

    def completion(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> LLMModelResponse:
        # Delegate to the top-level function
        litellm_kwargs = self._get_litellm_kwargs(**kwargs)
        response = litellm.completion(*args, **litellm_kwargs)
        cost_float = completion_cost(response)
        cost = f"{cost_float:.6f}" if cost_float is not None else None

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
        litellm_kwargs = self._get_litellm_kwargs(**kwargs)
        response: ModelResponse | CustomStreamWrapper = await litellm.acompletion(
            *args,
            **litellm_kwargs,
        )
        return response

    def get_available_models(self) -> List[str]:
        if self.provider in SUPPORTED_TEXT_MODELS:
            return SUPPORTED_TEXT_MODELS[self.provider]

        # if provider isn't in the pre-configured set of liteLLM cost
        # fallback to fetching from provider's API
        # this may return models the provider supports that are not text models
        # currently, there is no way to filter
        if self.provider == ModelProvider.VERTEX_AI:
            # For Vertex AI, pass project and location
            return litellm.get_valid_models(
                check_provider_endpoint=True,
                custom_llm_provider=self.provider,
                vertex_project=self.project_id,
                vertex_location=self.region,
            )
        else:
            return litellm.get_valid_models(
                api_key=self.api_key,
                check_provider_endpoint=True,
                custom_llm_provider=self.provider,
            )
