from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from litellm.types.utils import ModelResponse, TokenCountResponse
from pydantic import BaseModel, Field

from clients.llm.llm_client import LLMClient, LLMModelResponse
from utils.constants import DEFAULT_ORG_ID


def _make_token_count_response(total: int = 42) -> TokenCountResponse:
    return TokenCountResponse(
        total_tokens=total,
        request_model="test-model",
        model_used="test-model",
        tokenizer_type="test",
    )


class TestGetWeatherResponseClass(BaseModel):
    city: str = Field(..., description="The city to get the weather for.")
    temperature: int = Field(
        ...,
        description="The temperature in farenheit for the city.",
    )


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_llm_client_completion_response_format(
    mock_completion,
    mock_completion_cost,
):
    """
    Tests the LLM Client properly returns the BaseModel proivded for structured outputs
    or a ModelResponse for json_schema outputs/unstructured outputs
    """
    # create the mock llm client
    llm_client = LLMClient(provider="openai", api_key="test-key")

    # unstructured outputs response
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Test response",
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.000123

    completion_request = {
        "messages": [{"role": "user", "content": "Hello"}],
    }

    response = llm_client.completion(
        model="openai/gpt-4o",
        org_id=DEFAULT_ORG_ID,
        **completion_request,
    )
    assert isinstance(response, LLMModelResponse)
    assert isinstance(response.response, ModelResponse)
    assert response.response.choices[0].message.get("content") == "Test response"
    assert response.cost == "0.000123"

    # Test json_schema structured outputs
    completion_request["response_format"] = (
        {
            "type": "json_schema",
            "json_schema": {
                "name": "user_schema",
                "description": "User information",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "User's name"},
                    },
                    "required": ["name"],
                },
            },
        },
    )
    mock_response.choices[0].message = {
        "content": '{"name": "John Doe"}',
    }

    response = llm_client.completion(
        model="openai/gpt-4o",
        org_id=DEFAULT_ORG_ID,
        **completion_request,
    )
    assert isinstance(response, LLMModelResponse)
    assert isinstance(response.response, ModelResponse)
    assert response.response.choices[0].message.get("content") == '{"name": "John Doe"}'
    assert response.cost == "0.000123"

    # Test pydantic response format
    completion_request["response_format"] = TestGetWeatherResponseClass
    mock_response.choices[0].message = {
        "content": '{"city": "New York", "temperature": 70}',
    }

    response = llm_client.completion(
        model="openai/gpt-4o",
        org_id=DEFAULT_ORG_ID,
        **completion_request,
    )
    assert isinstance(response, LLMModelResponse)
    assert response.structured_output_response is not None
    assert isinstance(response.structured_output_response, TestGetWeatherResponseClass)
    assert response.structured_output_response.city == "New York"
    assert response.structured_output_response.temperature == 70
    assert response.cost == "0.000123"


# ---------------------------------------------------------------------------
# acount_tokens — verify provider-specific kwargs are forwarded to LiteLLM.
#
# Regression coverage for the fix in src/clients/llm/llm_client.py that routes
# acount_tokens through _add_provider_credentials, matching completion /
# acompletion. Before the fix, only api_key + api_base were forwarded, which
# broke summarize_and_emit_replace on every non-OpenAI provider.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_acount_tokens_forwards_provider_credentials():
    """Single consolidated coverage for the acount_tokens credential-routing fix.

    Each sub-case re-instantiates the AsyncMock for litellm.acount_tokens via a
    fresh ``patch(...)`` context so we get a clean call history per provider,
    while keeping fixture setup (helper, imports, asyncio marker) amortized.

    Sub-case label is asserted alongside each check so a failure pinpoints the
    provider that regressed.
    """
    vertex_creds = {"type": "service_account", "project_id": "my-project"}
    messages = [{"role": "user", "content": "hi"}]

    # ---- OpenAI ---------------------------------------------------------
    case = "openai"
    with patch(
        "clients.llm.llm_client.litellm.acount_tokens",
        new_callable=AsyncMock,
    ) as mock_acount_tokens:
        mock_acount_tokens.return_value = _make_token_count_response()
        llm_client = LLMClient(provider=ModelProvider.OPENAI, api_key="openai-key")

        result = await llm_client.acount_tokens(
            model="openai/gpt-4o",
            messages=messages,
        )

        assert isinstance(result, TokenCountResponse), case
        mock_acount_tokens.assert_awaited_once()
        kwargs = mock_acount_tokens.await_args.kwargs
        assert kwargs["model"] == "openai/gpt-4o", case
        assert kwargs["messages"] == messages, case
        assert kwargs["api_key"] == "openai-key", case
        # No Azure / Vertex / Bedrock keys should be present for OpenAI.
        for forbidden in (
            "api_version",
            "api_base",
            "vertex_project",
            "vertex_location",
            "vertex_credentials",
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_region_name",
        ):
            assert forbidden not in kwargs, f"{case}: unexpected kwarg {forbidden}"

    # ---- Azure (success) ------------------------------------------------
    case = "azure"
    with patch(
        "clients.llm.llm_client.litellm.acount_tokens",
        new_callable=AsyncMock,
    ) as mock_acount_tokens:
        mock_acount_tokens.return_value = _make_token_count_response()
        llm_client = LLMClient(
            provider=ModelProvider.AZURE,
            api_key="azure-key",
            api_base="https://example.openai.azure.com",
            api_version="2024-02-15-preview",
        )

        await llm_client.acount_tokens(
            model="azure/gpt-4o",
            messages=messages,
        )

        mock_acount_tokens.assert_awaited_once()
        kwargs = mock_acount_tokens.await_args.kwargs
        assert kwargs["api_key"] == "azure-key", case
        assert kwargs["api_base"] == "https://example.openai.azure.com", case
        assert kwargs["api_version"] == "2024-02-15-preview", case

    # ---- Azure (missing api_version raises BEFORE the await) ------------
    case = "azure-missing-api-version"
    with patch(
        "clients.llm.llm_client.litellm.acount_tokens",
        new_callable=AsyncMock,
    ) as mock_acount_tokens:
        llm_client = LLMClient(
            provider=ModelProvider.AZURE,
            api_key="azure-key",
            api_base="https://example.openai.azure.com",
            api_version=None,
        )

        with pytest.raises(
            ValueError,
            match="api_version is required for Azure provider",
        ):
            await llm_client.acount_tokens(
                model="azure/gpt-4o",
                messages=messages,
            )

        mock_acount_tokens.assert_not_awaited(), case

    # ---- Vertex AI ------------------------------------------------------
    case = "vertex_ai"
    with patch(
        "clients.llm.llm_client.litellm.acount_tokens",
        new_callable=AsyncMock,
    ) as mock_acount_tokens:
        mock_acount_tokens.return_value = _make_token_count_response()
        llm_client = LLMClient(
            provider=ModelProvider.VERTEX_AI,
            project_id="my-project",
            region="us-central1",
            vertex_credentials=vertex_creds,
        )

        await llm_client.acount_tokens(
            model="vertex_ai/gemini-pro",
            messages=messages,
        )

        mock_acount_tokens.assert_awaited_once()
        kwargs = mock_acount_tokens.await_args.kwargs
        assert kwargs["vertex_project"] == "my-project", case
        assert kwargs["vertex_location"] == "us-central1", case
        assert kwargs["vertex_credentials"] == vertex_creds, case

    # ---- Bedrock --------------------------------------------------------
    case = "bedrock"
    with patch(
        "clients.llm.llm_client.litellm.acount_tokens",
        new_callable=AsyncMock,
    ) as mock_acount_tokens:
        mock_acount_tokens.return_value = _make_token_count_response()
        llm_client = LLMClient(
            provider=ModelProvider.BEDROCK,
            region="us-east-1",
            aws_bedrock_credentials={
                "aws_access_key_id": "AKIAFAKE",
                "aws_secret_access_key": "SECRET",
            },
        )

        await llm_client.acount_tokens(
            model="bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
            messages=messages,
        )

        mock_acount_tokens.assert_awaited_once()
        kwargs = mock_acount_tokens.await_args.kwargs
        assert kwargs["aws_access_key_id"] == "AKIAFAKE", case
        assert kwargs["aws_secret_access_key"] == "SECRET", case
        assert kwargs["aws_region_name"] == "us-east-1", case
