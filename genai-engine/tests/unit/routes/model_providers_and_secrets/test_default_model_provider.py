import pytest
from arthur_common.models.llm_model_providers import ModelProvider

from repositories.model_provider_repository import ModelProviderRepository
from schemas.custom_exceptions import DefaultModelProviderNotSetException
from schemas.request_schemas import PutDefaultModelProvider
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.mark.unit_tests
def test_default_model_provider_lifecycle(client: GenaiEngineTestClientBase):
    headers = client.authorized_user_api_key_headers
    api = client.base_client
    api.delete("/api/v1/default_model_provider", headers=headers)
    api.delete("/api/v1/model_providers/gemini", headers=headers)

    # unset: both fields null
    response = api.get("/api/v1/default_model_provider", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"provider": None, "model_name": None}

    # a provider without credentials can't be the default
    response = api.put(
        "/api/v1/default_model_provider",
        json={"provider": "gemini", "model_name": "gemini-2.5-flash"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "model provider gemini is not configured"

    response = api.put(
        "/api/v1/model_providers/gemini",
        json={"api_key": "test-key"},
        headers=headers,
    )
    assert response.status_code == 201
    response = api.put(
        "/api/v1/default_model_provider",
        json={"provider": "gemini", "model_name": "gemini-2.5-flash"},
        headers=headers,
    )
    assert response.status_code == 204

    response = api.get("/api/v1/default_model_provider", headers=headers)
    assert response.json() == {
        "provider": "gemini",
        "model_name": "gemini-2.5-flash",
    }

    # the default provider's credentials can't be deleted out from under it
    response = api.delete("/api/v1/model_providers/gemini", headers=headers)
    assert response.status_code == 400
    assert "default model provider" in response.json()["detail"]

    response = api.delete("/api/v1/default_model_provider", headers=headers)
    assert response.status_code == 204
    response = api.get("/api/v1/default_model_provider", headers=headers)
    assert response.json() == {"provider": None, "model_name": None}

    response = api.delete("/api/v1/model_providers/gemini", headers=headers)
    assert response.status_code == 204


@pytest.mark.unit_tests
def test_resolve_model():
    repo = ModelProviderRepository(override_get_db_session())
    repo.clear_default_model_provider()

    # a real provider passes through untouched, default set or not
    assert repo.resolve_model(ModelProvider.OPENAI, "gpt-4o") == (
        ModelProvider.OPENAI,
        "gpt-4o",
    )

    # 'default' with nothing set fails with its own exception type
    with pytest.raises(DefaultModelProviderNotSetException):
        repo.resolve_model("default", "default")

    repo.set_model_provider_credentials(ModelProvider.ANTHROPIC)
    try:
        repo.set_default_model_provider(
            PutDefaultModelProvider(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-haiku-4-5",
            ),
        )
        assert repo.resolve_model("default", "default") == (
            ModelProvider.ANTHROPIC,
            "claude-haiku-4-5",
        )
    finally:
        repo.clear_default_model_provider()
        repo.delete_model_provider_credentials(ModelProvider.ANTHROPIC)
