from unittest.mock import patch

import httpx
import openai
import pytest
from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)

from schemas.custom_exceptions import (
    LLMContentFilterException,
    LLMExecutionException,
    LLMMaxRequestTokensException,
)
from scorer.llm_client import LLMExecutor
from tests.constants import (
    DEFAULT_AZURE_OPENAI_SETTINGS,
    DEFAULT_VANILLA_OPENAI_SETTINGS,
)


@pytest.mark.parametrize(
    "expected_instance, openai_executor",
    [
        (ChatOpenAI, DEFAULT_VANILLA_OPENAI_SETTINGS),
        (AzureChatOpenAI, DEFAULT_AZURE_OPENAI_SETTINGS),
    ],
    indirect=["openai_executor"],
)
@pytest.mark.unit_tests
def test_get_gpt_model(expected_instance, openai_executor: LLMExecutor):
    gpt_model = openai_executor.get_gpt_model()
    assert isinstance(gpt_model, expected_instance)


@pytest.mark.parametrize(
    "expected_instance, openai_executor",
    [
        (OpenAIEmbeddings, DEFAULT_VANILLA_OPENAI_SETTINGS),
        (AzureOpenAIEmbeddings, DEFAULT_AZURE_OPENAI_SETTINGS),
    ],
    indirect=["openai_executor"],
)
@pytest.mark.unit_tests
def test_get_embeddings_model(expected_instance, openai_executor: LLMExecutor):
    with patch(
        "config.extra_features.extra_feature_config.CHAT_ENABLED",
        return_value=True,
    ):
        embedding_model = openai_executor.get_embeddings_model()
        assert isinstance(embedding_model, expected_instance)


@pytest.mark.parametrize(
    "openai_executor",
    [DEFAULT_AZURE_OPENAI_SETTINGS],
    indirect=["openai_executor"],
)
@pytest.mark.unit_tests
def test_execute_raise_rate_limit_error(openai_executor: LLMExecutor):
    def f():
        request = httpx.Request(method="GET", url="http://example.com")
        response = httpx.Response(status_code=500, request=request)
        raise openai.RateLimitError(message="something", response=response, body=None)

    with pytest.raises(LLMExecutionException) as err:
        openai_executor.execute(f, "anything")
        assert (
            err.message
            == "GenAI Engine was unable to evaluate due to an upstream API rate limit"
        )


@pytest.mark.parametrize(
    "openai_executor",
    [DEFAULT_AZURE_OPENAI_SETTINGS],
    indirect=["openai_executor"],
)
@pytest.mark.unit_tests
def test_execute_raise_api_connection_error(openai_executor: LLMExecutor):
    def f():
        request = httpx.Request(method="GET", url="http://example.com")
        raise openai.APIConnectionError(message="something", request=request)

    with pytest.raises(LLMExecutionException) as err:
        openai_executor.execute(f, "anything")
        assert (
            err.message
            == "GenAI Engine was unable to evaluate due to an upstream API connection error"
        )


@pytest.mark.parametrize(
    "code, expected_exception, expected_message, openai_executor",
    [
        (
            "context_length_exceeded",
            LLMMaxRequestTokensException,
            "GenAI Engine was unable to evaluate due to max request token.",
            DEFAULT_AZURE_OPENAI_SETTINGS,
        ),
        (
            "rate_limit_exceeded",
            LLMExecutionException,
            "GenAI Engine was unable to evaluate due to upstream API rate limit",
            DEFAULT_AZURE_OPENAI_SETTINGS,
        ),
        (
            "insufficient_quota",
            LLMExecutionException,
            "GenAI Engine was unable to evaluate due to upstream API quota",
            DEFAULT_AZURE_OPENAI_SETTINGS,
        ),
        (
            "content_filter",
            LLMContentFilterException,
            "",
            DEFAULT_AZURE_OPENAI_SETTINGS,
        ),
        (
            "unknown",
            LLMExecutionException,
            "GenAI Engine was unable to evaluate due to an upstream API request error",
            DEFAULT_AZURE_OPENAI_SETTINGS,
        ),
    ],
    indirect=["openai_executor"],
)
@pytest.mark.unit_tests
def test_execute_raise_error_with_code(
    code,
    expected_exception,
    expected_message,
    openai_executor: LLMExecutor,
):
    def f():
        request = httpx.Request(method="GET", url="http://example.com")
        raise openai.APIError(message="something", request=request, body={"code": code})

    with pytest.raises(expected_exception) as err:
        openai_executor.execute(f, "anything")
        assert err.message == expected_message


@pytest.mark.unit_tests
def test_get_random_connection_details():
    result = LLMExecutor._get_random_connection_details(
        "model_name::example.com::api_key",
    )
    assert result == ("model_name", "example.com", "api_key")

    result = LLMExecutor._get_random_connection_details(
        "model_name::example.com::api_key,model_name2::example.com2::api_key2",
    )
    assert result in [
        ("model_name", "example.com", "api_key"),
        ("model_name2", "example.com2", "api_key2"),
    ]

    result = LLMExecutor._get_random_connection_details(
        "model_name::example.com::api_key, model_name2::example.com2::api_key2",
    )
    assert result in [
        ("model_name", "example.com", "api_key"),
        ("model_name2", "example.com2", "api_key2"),
    ]

    # OpenAI connection string with no endpoint
    result = LLMExecutor._get_random_connection_details(
        "model_name::::api_key",
    )
    assert result == ("model_name", None, "api_key")

    result = LLMExecutor._get_random_connection_details(
        "model_name::::api_key,model_name2::::api_key2",
    )
    assert result in [
        ("model_name", None, "api_key"),
        ("model_name2", None, "api_key2"),
    ]

    result = LLMExecutor._get_random_connection_details(
        "model_name::::api_key, model_name2::::api_key2",
    )
    assert result in [
        ("model_name", None, "api_key"),
        ("model_name2", None, "api_key2"),
    ]


@pytest.mark.unit_tests
def test_get_random_connection_details_empty():
    result = LLMExecutor._get_random_connection_details(
        "",
    )
    assert result == (None, None, None)

    result = LLMExecutor._get_random_connection_details(
        None,
    )
    assert result == (None, None, None)

    result = LLMExecutor._get_random_connection_details(
        "::::::",
    )
    assert result == (None, None, None)

    result = LLMExecutor._get_random_connection_details(
        "gpt-35-turbo-0125::::",
    )
    assert result == ("gpt-35-turbo-0125", None, None)

    result = LLMExecutor._get_random_connection_details(
        ":::abc",
    )
    assert result == (None, None, None)

    result = LLMExecutor._get_random_connection_details(
        "::::abc",
    )
    assert result == (None, None, "abc")
