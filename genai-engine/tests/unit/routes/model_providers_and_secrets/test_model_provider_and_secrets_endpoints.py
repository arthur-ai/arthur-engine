import os
from unittest.mock import MagicMock, patch

import pytest

from schemas.enums import ModelProvider
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
@patch("schemas.agentic_prompt_schemas.completion_cost")
def test_model_provider_lifecycle(
    mock_completion_cost, client: GenaiEngineTestClientBase
):
    mock_completion_cost.return_value = 0.001234

    # first validate listing providers shows all disabled
    response = client.base_client.get(
        f"/api/v1/model_providers",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["providers"]) == 3
    for provider in response.json()["providers"]:
        assert provider["provider"] in ModelProvider
        assert not provider["enabled"]

    # enable the openai provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # first validate all are disabled except openai
    response = client.base_client.get(
        f"/api/v1/model_providers",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["providers"]) == 3
    for provider in response.json()["providers"]:
        assert provider["provider"] in ModelProvider
        assert (
            provider["enabled"]
            if provider["provider"] == ModelProvider.OPENAI
            else not provider["enabled"]
        )

    # enable the anthropic provider
    response = client.base_client.put(
        f"/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # first validate all are disabled except openai and anthropic
    response = client.base_client.get(
        f"/api/v1/model_providers",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["providers"]) == 3
    for provider in response.json()["providers"]:
        assert provider["provider"] in ModelProvider
        assert (
            provider["enabled"]
            if provider["provider"] in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC]
            else not provider["enabled"]
        )

    # overwrite the openai provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        json={"api_key": "test-key2"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # remove the openai provider
    response = client.base_client.delete(
        f"/api/v1/model_providers/openai",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # first validate all are disabled except anthropic
    response = client.base_client.get(
        f"/api/v1/model_providers",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["providers"]) == 3
    for provider in response.json()["providers"]:
        assert provider["provider"] in ModelProvider
        assert (
            provider["enabled"]
            if provider["provider"] == ModelProvider.ANTHROPIC
            else not provider["enabled"]
        )


@pytest.mark.unit_tests
@patch("schemas.agentic_prompt_schemas.completion_cost")
def test_secret_rotation(mock_completion_cost, client: GenaiEngineTestClientBase):
    mock_completion_cost.return_value = 0.001234
    # set the encryption key to key1
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "originalEncryptionKey"},
    ):
        # enable the openai provider
        response = client.base_client.put(
            f"/api/v1/model_providers/openai",
            json={"api_key": "openaiKey"},
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 201

        # Mock litellm.completion to verify the API key is passed correctly
        with patch("litellm.completion") as mock_litellm_completion:
            # Configure the mock to return a successful response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = {"content": "test response"}
            mock_litellm_completion.return_value = mock_response

            # run a completion to verify the api key is retrieved as key1
            completion_request = {
                "model_provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}],
                "completion_request": {"stream": False},
            }

            response = client.base_client.post(
                "/api/v1/completions",
                json=completion_request,
                headers=client.authorized_user_api_key_headers,
            )
            assert response.status_code == 200

            # Verify that litellm.completion was called with the correct API key
            mock_litellm_completion.assert_called_once()
            call_args = mock_litellm_completion.call_args
            assert call_args[1]["api_key"] == "openaiKey"

    # Phase 2: Rotate secrets with new key format
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "newKey::originalEncryptionKey"},
    ):
        # Call the secrets rotation API with invalid role
        response = client.base_client.post(
            "/api/v1/secrets/rotation",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 403

        # Call the secrets rotation API with org admin
        response = client.base_client.post(
            "/api/v1/secrets/rotation",
            headers=client.authorized_org_admin_api_key_headers,
        )
        assert response.status_code == 204

    # Phase 3: Use only the new key and verify completion still works
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "newKey"},
    ):
        # Mock litellm.completion to verify the API key is still correctly retrieved
        with patch("litellm.completion") as mock_litellm_completion_after_rotation:
            # Configure the mock to return a successful response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = {
                "content": "test response after rotation"
            }
            mock_litellm_completion_after_rotation.return_value = mock_response

            # run a completion to verify the api key is still retrieved as key1 after rotation
            completion_request = {
                "model_provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello after rotation"}],
                "completion_request": {"stream": False},
            }

            response = client.base_client.post(
                "/api/v1/completions",
                json=completion_request,
                headers=client.authorized_user_api_key_headers,
            )
            assert response.status_code == 200

            # Verify that litellm.completion was called with the correct API key after rotation
            mock_litellm_completion_after_rotation.assert_called_once()
            call_args = mock_litellm_completion_after_rotation.call_args
            assert call_args[1]["api_key"] == "openaiKey"
