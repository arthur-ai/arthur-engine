from unittest.mock import MagicMock, patch

import pytest
from litellm.types.utils import ModelResponse
from pydantic import BaseModel, Field

from clients.llm.llm_client import LLMClient
from schemas.internal_llm_schemas import LLMModelResponse


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
        **completion_request,
    )
    assert isinstance(response, LLMModelResponse)
    assert isinstance(response.response, ModelResponse)
    assert response.response.choices[0].message.get("content") == "Test response"
    assert response.cost == 0.000123

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
        **completion_request,
    )
    assert isinstance(response, LLMModelResponse)
    assert isinstance(response.response, ModelResponse)
    assert response.response.choices[0].message.get("content") == '{"name": "John Doe"}'
    assert response.cost == 0.000123

    # Test pydantic response format
    completion_request["response_format"] = TestGetWeatherResponseClass
    mock_response.choices[0].message = {
        "content": '{"city": "New York", "temperature": 70}',
    }

    response = llm_client.completion(
        model="openai/gpt-4o",
        **completion_request,
    )
    assert isinstance(response, LLMModelResponse)
    assert response.structured_output_response is not None
    assert isinstance(response.structured_output_response, TestGetWeatherResponseClass)
    assert response.structured_output_response.city == "New York"
    assert response.structured_output_response.temperature == 70
    assert response.cost == 0.000123
