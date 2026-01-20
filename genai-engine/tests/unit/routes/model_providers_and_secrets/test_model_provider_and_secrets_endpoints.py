import os
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from litellm.types.utils import ModelResponse

from clients.llm.llm_client import SUPPORTED_TEXT_MODELS
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
def test_model_provider_lifecycle(
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    mock_completion_cost.return_value = 0.001234

    # first validate listing providers shows all disabled
    response = client.base_client.get(
        f"/api/v1/model_providers",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["providers"]) == 5
    for provider in response.json()["providers"]:
        assert provider["provider"] in ModelProvider
        assert not provider["enabled"]

    # enable the openai provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        data={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # first validate all are disabled except openai
    response = client.base_client.get(
        f"/api/v1/model_providers",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["providers"]) == 5
    for provider in response.json()["providers"]:
        assert provider["provider"] in ModelProvider
        assert (
            provider["enabled"]
            if provider["provider"] == ModelProvider.OPENAI
            else not provider["enabled"]
        )

    # validate we can list models for the provider
    # mock returned list
    SUPPORTED_TEXT_MODELS[ModelProvider.OPENAI] = ["gpt-5", "gpt-4.1"]
    response = client.base_client.get(
        f"/api/v1/model_providers/openai/available_models",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "openai"
    assert response.json()["available_models"] == ["gpt-5", "gpt-4.1"]

    # validate we can cannot list models for disabled provider
    response = client.base_client.get(
        f"/api/v1/model_providers/anthropic/available_models",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # enable the anthropic provider
    response = client.base_client.put(
        f"/api/v1/model_providers/anthropic",
        data={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # first validate all are disabled except openai and anthropic
    response = client.base_client.get(
        f"/api/v1/model_providers",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["providers"]) == 5
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
        data={"api_key": "test-key2"},
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
    assert len(response.json()["providers"]) == 5
    for provider in response.json()["providers"]:
        assert provider["provider"] in ModelProvider
        assert (
            provider["enabled"]
            if provider["provider"] == ModelProvider.ANTHROPIC
            else not provider["enabled"]
        )


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
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
            data={"api_key": "openaiKey"},
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 201

        # Mock litellm.completion to verify the API key is passed correctly
        with patch("litellm.completion") as mock_litellm_completion:
            # Configure the mock to return a successful response
            mock_response = MagicMock(spec=ModelResponse)
            mock_response.choices = [MagicMock()]
            mock_message = MagicMock()
            mock_message.content = "test response"
            mock_message.tool_calls = None
            mock_response.choices[0].message = mock_message
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
            mock_response = MagicMock(spec=ModelResponse)
            mock_response.choices = [MagicMock()]
            mock_message = MagicMock()
            mock_message.content = "test response after rotation"
            mock_message.tool_calls = None
            mock_response.choices[0].message = mock_message
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


@pytest.mark.unit_tests
def test_put_model_provider_validations(client: GenaiEngineTestClientBase):
    # verify attempting to add an api key for vertex ai fails
    response = client.base_client.put(
        f"/api/v1/model_providers/vertex_ai",
        data={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # verify attempting to add an aws access key without a secret access key fails for bedrock
    response = client.base_client.put(
        f"/api/v1/model_providers/bedrock",
        data={"aws_access_key_id": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # verify attempting to add an aws secret access key without an aws access key fails for bedrock
    response = client.base_client.put(
        f"/api/v1/model_providers/bedrock",
        data={"aws_secret_access_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # verify other providers outside of bedrock fail if no api key is provided
    response = client.base_client.put(
        f"/api/v1/model_providers/anthropic",
        data={},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # verify credentials file with non-JSON content type fails
    response = client.base_client.put(
        f"/api/v1/model_providers/vertex_ai",
        data={},
        files={
            "credentials_file": ("credentials.txt", b'{"test": "data"}', "text/plain"),
        },
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert "must be a JSON file" in response.json()["detail"]


@pytest.mark.unit_tests
def test_setting_vertex_ai_provider_credentials(client: GenaiEngineTestClientBase):
    # Enabling vertex ai without any credentials should work since it will default to using the default credentials
    response = client.base_client.put(
        f"/api/v1/model_providers/vertex_ai",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Enabling vertex ai with json credentials file
    response = client.base_client.put(
        f"/api/v1/model_providers/vertex_ai",
        files={
            "credentials_file": (
                "credentials.txt",
                b'{"type": "service_account", "project_id": "test-project", "private_key_id": "test-key", "private_key": "test-key", "client_email": "test-email", "client_id": "test-id", "auth_uri": "test-auth-uri", "token_uri": "test-token-uri", "auth_provider_x509_cert_url": "test-auth-provider-x509-cert-url", "client_x509_cert_url": "test-client-x509-cert-url", "universe_domain": "test-universe-domain"}',
                "application/json",
            ),
        },
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Cleanup
    response = client.base_client.delete(
        f"/api/v1/model_providers/vertex_ai",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204


@pytest.mark.unit_tests
def test_setting_bedrock_provider_credentials(client: GenaiEngineTestClientBase):
    # Enabling bedrock with no credentials should work because it will default to using attached credentials
    response = client.base_client.put(
        f"/api/v1/model_providers/bedrock",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Enabling bedrock with an api key
    response = client.base_client.put(
        f"/api/v1/model_providers/bedrock",
        data={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Enabling bedrock with access key, secret access key and optional region
    response = client.base_client.put(
        f"/api/v1/model_providers/bedrock",
        data={
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-key",
            "region": "us-east-1",
        },
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Enabling bedrock with endpoint
    response = client.base_client.put(
        f"/api/v1/model_providers/bedrock",
        data={"aws_bedrock_runtime_endpoint": "test-endpoint"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Enabling bedrock with role and session name
    response = client.base_client.put(
        f"/api/v1/model_providers/bedrock",
        data={"aws_role_name": "test-role", "aws_session_name": "test-session"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Cleanup
    response = client.base_client.delete(
        f"/api/v1/model_providers/bedrock",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204
