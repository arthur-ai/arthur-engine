from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from litellm.litellm_core_utils.llm_response_utils.convert_dict_to_response import (
    convert_to_model_response_object,
)
from litellm.llms.anthropic.chat.transformation import AnthropicConfig
from litellm.llms.bedrock.chat.converse_transformation import AmazonConverseConfig
from litellm.llms.bedrock.chat.invoke_transformations.anthropic_claude3_transformation import (
    AmazonAnthropicClaudeConfig,
)
from litellm.llms.vertex_ai.vertex_ai_partner_models.anthropic.transformation import (
    VertexAIAnthropicConfig,
)
from litellm.types.utils import ModelResponse, TokenCountResponse, Usage
from pydantic import BaseModel, Field

from clients.llm.llm_client import LLMClient, LLMModelResponse, LLMTokenUsage
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
# completion / acompletion with tools — run LiteLLM for real (via its built-in
# mock_response) instead of patching it out.
#
# Regression coverage for UP-5288: whenever `tools` is passed, LiteLLM imports
# its MCP gateway handler, which since 1.106.0 needs the `mcp` package from the
# litellm[mcp] extra. Every tool-calling feature (AI Assistant, playground,
# experiments) 500'd while the mocked tests above stayed green.
# ---------------------------------------------------------------------------

_FUNCTION_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "parameters": {"type": "object", "properties": {}},
    },
}


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.record_org_token_usage")
@patch("clients.llm.llm_client.enforce_token_quota")
def test_llm_client_completion_with_tools(
    mock_enforce_token_quota,
    mock_record_org_token_usage,
):
    llm_client = LLMClient(provider=ModelProvider.OPENAI, api_key="test-key")

    response = llm_client.completion(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
        tools=[_FUNCTION_TOOL],
        mock_response="Test response",
        org_id=DEFAULT_ORG_ID,
    )

    assert response.response.choices[0].message.get("content") == "Test response"


@pytest.mark.unit_tests
@pytest.mark.asyncio
@patch("clients.llm.llm_client.record_org_token_usage")
@patch("clients.llm.llm_client.enforce_token_quota")
async def test_llm_client_acompletion_with_tools(
    mock_enforce_token_quota,
    mock_record_org_token_usage,
):
    llm_client = LLMClient(provider=ModelProvider.OPENAI, api_key="test-key")

    response = await llm_client.acompletion(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
        tools=[_FUNCTION_TOOL],
        mock_response="Test response",
        org_id=DEFAULT_ORG_ID,
    )

    assert response.choices[0].message.get("content") == "Test response"


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


@pytest.mark.unit_tests
def test_token_usage_from_openai_shaped_response():
    response = ModelResponse(
        usage=Usage(
            prompt_tokens=1200,
            completion_tokens=40,
            total_tokens=1240,
            prompt_tokens_details={"cached_tokens": 1024},
        ),
    )

    usage = LLMTokenUsage.from_response(response)

    assert usage == LLMTokenUsage(
        prompt_tokens=1200,
        completion_tokens=40,
        cache_read_tokens=1024,
        cache_write_tokens=None,
    )


@pytest.mark.unit_tests
def test_token_usage_from_anthropic_shaped_response():
    response = ModelResponse(
        usage=Usage(
            prompt_tokens=1500,
            completion_tokens=60,
            total_tokens=1560,
            cache_read_input_tokens=900,
            cache_creation_input_tokens=400,
        ),
    )

    usage = LLMTokenUsage.from_response(response)

    assert usage == LLMTokenUsage(
        prompt_tokens=1500,
        completion_tokens=60,
        cache_read_tokens=900,
        cache_write_tokens=400,
    )


@pytest.mark.unit_tests
def test_token_usage_falls_back_to_raw_anthropic_fields():
    response = MagicMock()
    response.usage = MagicMock(
        prompt_tokens=300,
        completion_tokens=20,
        prompt_tokens_details=None,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=250,
    )

    usage = LLMTokenUsage.from_response(response)

    assert usage.cache_read_tokens == 0
    assert usage.cache_write_tokens == 250


@pytest.mark.unit_tests
def test_token_usage_missing_usage_is_null():
    response = MagicMock(spec=ModelResponse)
    response.usage = None

    assert LLMTokenUsage.from_response(response) == LLMTokenUsage()
    assert LLMTokenUsage.from_response(None) == LLMTokenUsage()
    # Mocked responses without real usage must not leak mock values into the counts
    assert LLMTokenUsage.from_response(MagicMock(spec=ModelResponse)) == LLMTokenUsage()


# Raw provider payloads, run through litellm's own response transformation below. Anthropic's
# input_tokens and Bedrock Converse's inputTokens both exclude cache reads and writes; litellm
# adds them back into prompt_tokens, so every provider stores total input tokens.
_ANTHROPIC_MESSAGES_BODY = {
    "id": "msg_1",
    "type": "message",
    "role": "assistant",
    "model": "claude-sonnet-4-5",
    "content": [{"type": "text", "text": "ok"}],
    "stop_reason": "end_turn",
    "usage": {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_read_input_tokens": 900,
        "cache_creation_input_tokens": 400,
    },
}

_BEDROCK_CONVERSE_BODY = {
    "output": {"message": {"role": "assistant", "content": [{"text": "ok"}]}},
    "stopReason": "end_turn",
    "usage": {
        "inputTokens": 100,
        "outputTokens": 20,
        "totalTokens": 1420,
        "cacheReadInputTokens": 900,
        "cacheWriteInputTokens": 400,
    },
    "metrics": {"latencyMs": 1},
}


def _transform_provider_response(config, model: str, body: dict) -> ModelResponse:
    return config.transform_response(
        model=model,
        raw_response=httpx.Response(
            200,
            json=body,
            request=httpx.Request("POST", "https://provider.test"),
        ),
        model_response=ModelResponse(),
        logging_obj=MagicMock(),
        request_data={},
        messages=[{"role": "user", "content": "hi"}],
        optional_params={},
        litellm_params={},
        encoding=None,
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "config,model,body",
    [
        (AnthropicConfig(), "claude-sonnet-4-5", _ANTHROPIC_MESSAGES_BODY),
        (
            AmazonConverseConfig(),
            "anthropic.claude-sonnet-4-5-20250929-v1:0",
            _BEDROCK_CONVERSE_BODY,
        ),
        (
            AmazonAnthropicClaudeConfig(),
            "anthropic.claude-sonnet-4-5-20250929-v1:0",
            _ANTHROPIC_MESSAGES_BODY,
        ),
        (
            VertexAIAnthropicConfig(),
            "claude-sonnet-4-5@20250929",
            _ANTHROPIC_MESSAGES_BODY,
        ),
    ],
    ids=["anthropic", "bedrock_converse", "bedrock_invoke_claude", "vertex_ai_claude"],
)
def test_token_usage_prompt_tokens_include_cache_for_claude_providers(
    config,
    model,
    body,
):
    response = _transform_provider_response(config, model, body)

    assert LLMTokenUsage.from_response(response) == LLMTokenUsage(
        prompt_tokens=1400,
        completion_tokens=20,
        cache_read_tokens=900,
        cache_write_tokens=400,
    )


@pytest.mark.unit_tests
def test_token_usage_bedrock_converse_without_cache_is_zero():
    body = {
        **_BEDROCK_CONVERSE_BODY,
        "usage": {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120},
    }

    response = _transform_provider_response(
        AmazonConverseConfig(),
        "anthropic.claude-sonnet-4-5-20250929-v1:0",
        body,
    )

    assert LLMTokenUsage.from_response(response) == LLMTokenUsage(
        prompt_tokens=100,
        completion_tokens=20,
        cache_read_tokens=0,
        cache_write_tokens=0,
    )


@pytest.mark.unit_tests
def test_token_usage_openai_prompt_tokens_already_include_cache():
    response = convert_to_model_response_object(
        response_object={
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                },
            ],
            "usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 40,
                "total_tokens": 1240,
                "prompt_tokens_details": {"cached_tokens": 1024},
            },
        },
        model_response_object=ModelResponse(),
    )

    assert LLMTokenUsage.from_response(response) == LLMTokenUsage(
        prompt_tokens=1200,
        completion_tokens=40,
        cache_read_tokens=1024,
        cache_write_tokens=None,
    )
