import uuid
from datetime import datetime

import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from pydantic import SecretStr

from clients.llm.llm_client import SUPPORTED_TEXT_MODELS
from db_models.secret_storage_models import DatabaseSecretStorage
from repositories.model_provider_repository import ModelProviderRepository
from schemas.enums import SecretType
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture(scope="function")
def db_session():
    return override_get_db_session()


@pytest.fixture(scope="function")
def openai_provider(db_session):
    """An enabled openai provider row, removed after the test."""
    row = DatabaseSecretStorage(
        id=str(uuid.uuid4()),
        name=ModelProvider.OPENAI,
        value={"api_key": "test-key"},
        secret_type=SecretType.MODEL_PROVIDER,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    db_session.commit()
    yield row
    db_session.delete(row)
    db_session.commit()


@pytest.fixture(scope="function")
def catalog(monkeypatch):
    """Stub the litellm-derived catalog. setitem restores it after the test."""

    def _set(models: list[str]) -> None:
        monkeypatch.setitem(SUPPORTED_TEXT_MODELS, ModelProvider.OPENAI, models)

    return _set


@pytest.mark.unit_tests
def test_null_whitelist_returns_full_catalog(db_session, openai_provider, catalog):
    catalog(["gpt-5", "gpt-4.1", "gpt-4o"])
    repo = ModelProviderRepository(db_session)

    assert repo.get_model_whitelist(ModelProvider.OPENAI) is None
    assert repo.list_models_for_provider(ModelProvider.OPENAI) == [
        "gpt-5",
        "gpt-4.1",
        "gpt-4o",
    ]


@pytest.mark.unit_tests
def test_whitelist_filters_and_preserves_catalog_order(
    db_session,
    openai_provider,
    catalog,
):
    catalog(["gpt-5", "gpt-4.1", "gpt-4o"])
    repo = ModelProviderRepository(db_session)
    # Saved in a different order than the catalog, to prove ordering is
    # catalog-driven rather than whitelist-driven.
    repo.set_model_whitelist(ModelProvider.OPENAI, ["gpt-4o", "gpt-5"])

    assert repo.get_model_whitelist(ModelProvider.OPENAI) == ["gpt-4o", "gpt-5"]
    assert repo.list_models_for_provider(ModelProvider.OPENAI) == ["gpt-5", "gpt-4o"]


@pytest.mark.unit_tests
def test_stale_whitelist_entry_is_dropped_not_raised(
    db_session,
    openai_provider,
    catalog,
):
    catalog(["gpt-5"])
    repo = ModelProviderRepository(db_session)
    repo.set_model_whitelist(ModelProvider.OPENAI, ["gpt-5", "gpt-retired"])

    assert repo.list_models_for_provider(ModelProvider.OPENAI) == ["gpt-5"]


@pytest.mark.unit_tests
def test_catalog_lookup_ignores_whitelist(db_session, openai_provider, catalog):
    catalog(["gpt-5", "gpt-4.1"])
    repo = ModelProviderRepository(db_session)
    repo.set_model_whitelist(ModelProvider.OPENAI, ["gpt-5"])

    assert repo.list_catalog_models_for_provider(ModelProvider.OPENAI) == [
        "gpt-5",
        "gpt-4.1",
    ]


@pytest.mark.unit_tests
def test_clearing_whitelist_restores_unfiltered(db_session, openai_provider, catalog):
    catalog(["gpt-5", "gpt-4.1"])
    repo = ModelProviderRepository(db_session)
    repo.set_model_whitelist(ModelProvider.OPENAI, ["gpt-5"])
    repo.set_model_whitelist(ModelProvider.OPENAI, None)

    assert repo.get_model_whitelist(ModelProvider.OPENAI) is None
    assert repo.list_models_for_provider(ModelProvider.OPENAI) == ["gpt-5", "gpt-4.1"]


@pytest.mark.unit_tests
def test_credential_update_preserves_whitelist(db_session, openai_provider):
    repo = ModelProviderRepository(db_session)
    repo.set_model_whitelist(ModelProvider.OPENAI, ["gpt-5"])

    repo.set_model_provider_credentials(
        provider=ModelProvider.OPENAI,
        api_key=SecretStr("rotated-key"),
    )

    assert repo.get_model_whitelist(ModelProvider.OPENAI) == ["gpt-5"]


@pytest.mark.unit_tests
def test_whitelist_for_unconfigured_provider_is_none(db_session):
    repo = ModelProviderRepository(db_session)

    assert repo.get_model_whitelist(ModelProvider.GEMINI) is None


@pytest.mark.unit_tests
def test_catalog_available_without_credentials(db_session, monkeypatch):
    """Models can be curated before any secret row exists."""
    monkeypatch.setitem(
        SUPPORTED_TEXT_MODELS,
        ModelProvider.GEMINI,
        ["gemini-2.5-pro", "gemini-2.5-flash"],
    )
    repo = ModelProviderRepository(db_session)

    assert repo.list_catalog_models_for_provider(ModelProvider.GEMINI) == [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ]


@pytest.mark.unit_tests
def test_vllm_catalog_still_requires_configuration(db_session, monkeypatch):
    """vLLM has no static catalog — its models come from its own endpoint, which
    needs a stored api_base."""
    monkeypatch.delitem(SUPPORTED_TEXT_MODELS, ModelProvider.VLLM, raising=False)
    repo = ModelProviderRepository(db_session)

    with pytest.raises(HTTPException) as excinfo:
        repo.list_catalog_models_for_provider(ModelProvider.VLLM)
    assert excinfo.value.status_code == 400


@pytest.mark.unit_tests
def test_static_catalog_is_read_through_accessor_not_a_stale_binding(monkeypatch):
    """refresh_models_periodically rebinds SUPPORTED_TEXT_MODELS to a fresh dict every
    8 hours. get_static_catalog must observe that rebinding, or every deployment would
    serve a frozen catalog after the first refresh."""
    import clients.llm.llm_client as llm_client

    monkeypatch.setattr(
        llm_client,
        "SUPPORTED_TEXT_MODELS",
        {ModelProvider.OPENAI: ["rebound-model"]},
    )

    assert llm_client.get_static_catalog(ModelProvider.OPENAI) == ["rebound-model"]
