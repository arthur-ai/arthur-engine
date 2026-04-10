import logging
import threading
import time
from typing import Any, List, Optional, Union

import httpx
import litellm
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from litellm import completion_cost, get_model_cost_map, model_cost_map_url
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.utils import ModelResponse, TextCompletionResponse
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class LLMModelResponse(BaseModel):
    # NOTE: We use arbitrary_types_allowed=True here to allow the response parameter to be the non-pydantic types ModelResponse/CustomStreamWrapper
    model_config = ConfigDict(arbitrary_types_allowed=True)

    response: Union[ModelResponse, CustomStreamWrapper] = Field(
        ...,
        description="The raw response from litellm",
    )
    structured_output_response: Optional[BaseModel] = Field(
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

        # Normalize all vertex_ai variants (vertex_ai-language-models, vertex_ai-anthropic_models, etc.)
        # to single "vertex_ai" key for consistent lookup
        if provider.startswith("vertex_ai"):
            provider = "vertex_ai"

        model_name = model_name.replace(f"{provider}/", "")

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
        api_key: str | None = None,
        project_id: str | None = None,
        region: str | None = None,
        api_base: str | None = None,
        vertex_credentials: dict[str, str] | None = None,
        aws_bedrock_credentials: dict[str, str] | None = None,
    ):
        self.provider = provider
        self.api_key = api_key
        self.project_id = project_id
        self.region = region
        self.api_base = api_base
        self.vertex_credentials = vertex_credentials
        self.aws_bedrock_credentials = aws_bedrock_credentials

    def _add_provider_credentials(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self.api_key:
            kwargs["api_key"] = self.api_key

        if self.provider == ModelProvider.VERTEX_AI:
            if self.project_id:
                kwargs["vertex_project"] = self.project_id
            if self.region:
                kwargs["vertex_location"] = self.region
            if self.vertex_credentials is not None:
                kwargs["vertex_credentials"] = self.vertex_credentials
            else:
                logger.warning(
                    "Using default credentials. If there is no attached service account or cli authenticated user this will fail",
                )
        elif self.provider == ModelProvider.BEDROCK:
            if self.aws_bedrock_credentials is not None:
                if self.aws_bedrock_credentials.get("aws_access_key_id"):
                    kwargs["aws_access_key_id"] = self.aws_bedrock_credentials.get(
                        "aws_access_key_id",
                    )
                if self.aws_bedrock_credentials.get("aws_secret_access_key"):
                    kwargs["aws_secret_access_key"] = self.aws_bedrock_credentials.get(
                        "aws_secret_access_key",
                    )
                if self.aws_bedrock_credentials.get("aws_bedrock_runtime_endpoint"):
                    kwargs["aws_bedrock_runtime_endpoint"] = (
                        self.aws_bedrock_credentials.get("aws_bedrock_runtime_endpoint")
                    )
                if self.aws_bedrock_credentials.get("aws_role_name"):
                    kwargs["aws_role_name"] = self.aws_bedrock_credentials.get(
                        "aws_role_name",
                    )
                if self.aws_bedrock_credentials.get("aws_session_name"):
                    kwargs["aws_session_name"] = self.aws_bedrock_credentials.get(
                        "aws_session_name",
                    )

            if self.region:
                kwargs["aws_region_name"] = self.region

            if (
                "aws_access_key_id" in kwargs and "aws_secret_access_key" not in kwargs
            ) or (
                "aws_access_key_id" not in kwargs and "aws_secret_access_key" in kwargs
            ):
                raise ValueError(
                    "aws_access_key_id and aws_secret_access_key must be provided together",
                )
        elif self.provider == ModelProvider.VLLM:
            if self.api_base:
                kwargs["api_base"] = self.api_base
            else:
                raise ValueError("api_base is required for this provider")

        return kwargs

    def calculate_cost(
        self, response: Optional[Union[ModelResponse, TextCompletionResponse]]
    ) -> str:
        """Calculate the cost of an LLM response, returning '0.00' if cost data is unavailable."""
        if response is None:
            return "0.00"
        if self.provider == ModelProvider.VLLM:
            logger.warning("Cost calculation is not supported for the VLLM provider")
            return "0.00"
        try:
            cost_float = completion_cost(response)
            return f"{cost_float:.6f}"
        except Exception:
            model_name = getattr(response, "model", "unknown")
            logger.warning(f"Cost calculation not available for model={model_name}")
            return "0.00"

    def completion(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> LLMModelResponse:
        # Delegate to the top-level function
        kwargs = self._add_provider_credentials(kwargs)

        try:
            response = litellm.completion(*args, **kwargs)
        except litellm.BadRequestError as e:
            if "requires at least one non-system message" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail=f"Provider '{self.provider}' requires at least one non-system message.",
                )
            raise HTTPException(
                status_code=400,
                detail=f"Bad request to provider '{self.provider}': {str(e)}",
            )
        except litellm.NotFoundError as e:
            # Model not found or not available
            error_msg = str(e)
            # Extract a cleaner error message
            if "was not found" in error_msg or "NOT_FOUND" in error_msg:
                model = kwargs.get("model", "unknown")
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' is not available or not found for provider '{self.provider}'. Please check that the model exists and you have access to it.",
                )
            raise HTTPException(status_code=404, detail=f"Model not found: {error_msg}")
        except litellm.AuthenticationError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed for provider '{self.provider}': {str(e)}",
            )
        except litellm.RateLimitError as e:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for provider '{self.provider}': {str(e)}",
            )
        except litellm.ServiceUnavailableError as e:
            # ServiceUnavailableError can wrap other errors
            error_msg = str(e)
            if "NotFoundError" in error_msg and (
                "was not found" in error_msg or "NOT_FOUND" in error_msg
            ):
                model = kwargs.get("model", "unknown")
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' is not available or not found for provider '{self.provider}'. Please check that the model exists and you have access to it.",
                )
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable for provider '{self.provider}': {error_msg}",
            )
        except litellm.APIError as e:
            raise HTTPException(
                status_code=e.status_code if hasattr(e, "status_code") else 500,
                detail=f"API error from provider '{self.provider}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error during completion: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during completion: {str(e)}",
            )

        cost = self.calculate_cost(response)

        llm_model_response = LLMModelResponse(
            response=response,
            cost=cost,
            structured_output_response=None,
        )

        message_content: Optional[str] = None
        if (
            response
            and response.choices
            and response.choices[0].message
            and response.choices[0].message.get("content") is not None
        ):
            message_content = response.choices[0].message.get("content")

        if (
            "response_format" in kwargs
            and isinstance(kwargs["response_format"], type)
            and issubclass(kwargs["response_format"], BaseModel)
            and message_content is not None
        ):
            response_format: type[BaseModel] = kwargs["response_format"]
            loaded_response = response_format.model_validate_json(message_content)
            llm_model_response.structured_output_response = loaded_response

        return llm_model_response

    async def acompletion(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> ModelResponse | CustomStreamWrapper:
        # Delegate to the top-level function
        kwargs = self._add_provider_credentials(kwargs)

        try:
            response: ModelResponse | CustomStreamWrapper = await litellm.acompletion(
                *args,
                **kwargs,
            )
            return response
        except litellm.BadRequestError as e:
            if "requires at least one non-system message" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail=f"Provider '{self.provider}' requires at least one non-system message.",
                )
            raise HTTPException(
                status_code=400,
                detail=f"Bad request to provider '{self.provider}': {str(e)}",
            )
        except litellm.NotFoundError as e:
            # Model not found or not available
            error_msg = str(e)
            # Extract a cleaner error message
            if "was not found" in error_msg or "NOT_FOUND" in error_msg:
                model = kwargs.get("model", "unknown")
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' is not available or not found for provider '{self.provider}'. Please check that the model exists and you have access to it.",
                )
            raise HTTPException(status_code=404, detail=f"Model not found: {error_msg}")
        except litellm.AuthenticationError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed for provider '{self.provider}': {str(e)}",
            )
        except litellm.RateLimitError as e:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for provider '{self.provider}': {str(e)}",
            )
        except litellm.ServiceUnavailableError as e:
            # ServiceUnavailableError can wrap other errors
            error_msg = str(e)
            if "NotFoundError" in error_msg and (
                "was not found" in error_msg or "NOT_FOUND" in error_msg
            ):
                model = kwargs.get("model", "unknown")
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' is not available or not found for provider '{self.provider}'. Please check that the model exists and you have access to it.",
                )
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable for provider '{self.provider}': {error_msg}",
            )
        except litellm.APIError as e:
            raise HTTPException(
                status_code=e.status_code if hasattr(e, "status_code") else 500,
                detail=f"API error from provider '{self.provider}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error during completion: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during completion: {str(e)}",
            )

    def get_available_models(self) -> List[str]:
        if self.provider in SUPPORTED_TEXT_MODELS:
            return SUPPORTED_TEXT_MODELS[self.provider]

        # Special handling for vLLM - LiteLLM has a bug where get_models always fails
        # because it checks if api_key is None, but get_api_key() always returns None for vLLM
        # So we call the vLLM /v1/models endpoint directly
        if self.provider == ModelProvider.VLLM:
            if not self.api_base:
                logger.error("api_base is required for vLLM provider")
                return []

            try:
                # Construct the models endpoint URL
                api_base = self.api_base.rstrip("/")
                models_url = f"{api_base}/models"

                # Prepare headers
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # Make request to vLLM models endpoint
                response = httpx.get(models_url, headers=headers, timeout=10.0)
                response.raise_for_status()

                # Parse the response - vLLM follows OpenAI API format
                data = response.json()
                models = [model["id"] for model in data.get("data", [])]
                logger.info(f"Fetched {len(models)} models from vLLM endpoint")
                return models
            except Exception as e:
                logger.error(f"Failed to fetch models from vLLM endpoint: {e}")
                return []

        # if provider isn't in the pre-configured set of liteLLM cost
        # fallback to fetching from provider's API
        # this may return models the provider supports that are not text models
        # currently, there is no way to filter
        return litellm.get_valid_models(
            api_key=self.api_key,
            check_provider_endpoint=True,
            custom_llm_provider=self.provider,
        )
