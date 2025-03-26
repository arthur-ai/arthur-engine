import pytest
from config.openai_config import OpenAISettings
from pydantic import ValidationError


def test_check_url_raises_error():
    # Test that a ValidationError is raised when the URL does not end with '/'
    with pytest.raises(ValidationError):
        OpenAISettings(
            GENAI_ENGINE_OPENAI_PROVIDER="OpenAI",
            GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD=10,
            GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS=60,
            GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS="gpt-3.5-turbo-0125::https://api.openai.com/v1::abcdefg,"
            "gpt-3.5-turbo-0614::https://api.openai.com/v1::abcdefg",
            GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS="text-embedding-ada-001::https://api.openai.com/v1::abcdefg,"
            "text-embedding-ada-002::https://api.openai.com/v1::abcdefg",
        )
    with pytest.raises(ValidationError):
        OpenAISettings(
            GENAI_ENGINE_OPENAI_PROVIDER="OpenAI",
            GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD=10,
            GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS=60,
            GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS="gpt-3.5-turbo-0125::https://api.openai.com/v1/::abcdefg,"
            "gpt-3.5-turbo-0614::https://api.openai.com/v1/::abcdefg",
            GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS="text-embedding-ada-001::https://api.openai.com/v1/::abcdefg,"
            "text-embedding-ada-002::https://api.openai.com/v1::abcdefg",
        )


def test_check_url_no_error():
    OpenAISettings(
        GENAI_ENGINE_OPENAI_PROVIDER="OpenAI",
        GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD=10,
        GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS=60,
        GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS="gpt-3.5-turbo-0125::https://api.openai.com/v1/::abcdefg,"
        "gpt-3.5-turbo-0614::https://api.openai.com/v1/::abcdefg",
        GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS="text-embedding-ada-001::https://api.openai.com/v1/::abcdefg,"
        "text-embedding-ada-002::https://api.openai.com/v1/::abcdefg",
    )
