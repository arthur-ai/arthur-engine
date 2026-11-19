import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException

from repositories.model_provider_repository import ModelProviderRepository
from schemas.custom_exceptions import DefaultModelProviderNotSetException
from schemas.request_schemas import PutDefaultModelProvider
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)

# The default model provider is instance-wide state, so tests that set it share one worker
pytestmark = pytest.mark.xdist_group("default_model_provider")


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

    try:
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

    finally:
        # leave no default or Gemini credentials behind, even after a failed assertion
        api.delete("/api/v1/default_model_provider", headers=headers)
        api.delete("/api/v1/model_providers/gemini", headers=headers)


@pytest.mark.unit_tests
def test_resolve_model():
    repo = ModelProviderRepository(override_get_db_session())
    repo.clear_default_model_provider()

    # a real provider passes through untouched, default set or not
    assert repo.resolve_model(ModelProvider.OPENAI, "gpt-4o") == (
        ModelProvider.OPENAI,
        "gpt-4o",
    )

    # an explicit provider needs a model name
    with pytest.raises(HTTPException) as exc:
        repo.resolve_model(ModelProvider.OPENAI, None)
    assert exc.value.status_code == 400

    # the 'empty' placeholder and an unset provider both use the default;
    # with nothing set they fail with its own exception type
    for stored in ("empty", None):
        with pytest.raises(DefaultModelProviderNotSetException):
            repo.resolve_model(stored, None)

    repo.set_model_provider_credentials(ModelProvider.ANTHROPIC)
    try:
        repo.set_default_model_provider(
            PutDefaultModelProvider(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-haiku-4-5",
            ),
        )
        for stored in ("empty", None):
            assert repo.resolve_model(stored, None) == (
                ModelProvider.ANTHROPIC,
                "claude-haiku-4-5",
            )
    finally:
        repo.clear_default_model_provider()
        repo.delete_model_provider_credentials(ModelProvider.ANTHROPIC)


@pytest.mark.unit_tests
def test_synthetic_data_prompt_status_reports_the_default(
    client: GenaiEngineTestClientBase,
):
    headers = client.authorized_user_api_key_headers
    api = client.base_client
    api.delete("/api/v1/default_model_provider", headers=headers)

    # no default: the synthetic data prompt is still a placeholder
    response = api.get("/api/v2/datasets/synthetic-data/prompt-status", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "model_provider": "empty",
        "model_name": "empty",
        "is_placeholder": True,
        "uses_default_model": False,
    }

    api.put("/api/v1/model_providers/openai", json={"api_key": "k"}, headers=headers)
    try:
        api.put(
            "/api/v1/default_model_provider",
            json={"provider": "openai", "model_name": "gpt-4.1-mini"},
            headers=headers,
        )
        # with a default, the placeholder runs on it, so the UI pre-fills it
        response = api.get(
            "/api/v2/datasets/synthetic-data/prompt-status",
            headers=headers,
        )
        assert response.json() == {
            "model_provider": "openai",
            "model_name": "gpt-4.1-mini",
            "is_placeholder": False,
            "uses_default_model": True,
        }
    finally:
        api.delete("/api/v1/default_model_provider", headers=headers)
        api.delete("/api/v1/model_providers/openai", headers=headers)
