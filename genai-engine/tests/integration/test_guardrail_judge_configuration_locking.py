import os
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from db_models import DatabaseApplicationConfiguration, DatabaseOrganization
from db_models.secret_storage_models import DatabaseSecretStorage
from repositories.guardrail_configuration_repository import (
    GuardrailConfigurationRepository,
    lock_guardrail_configuration,
)
from repositories.model_provider_repository import ModelProviderRepository
from schemas.guardrail_schemas import GuardrailLLMConfiguration
from services.guardrails import llm_configuration_service as configuration_service
from services.guardrails.judge_executor import CONFIGURATION_UNAVAILABLE
from utils.constants import ORG_ADMIN, TASK_ADMIN

pytestmark = pytest.mark.integration_tests


@pytest.fixture(scope="module", autouse=True)
def client():
    yield None


@pytest.fixture
def postgres_store(monkeypatch, tmp_path):
    address = os.environ.get("GUARDRAIL_TEST_POSTGRES_URL")
    if not address:
        pytest.skip(
            "Set GUARDRAIL_TEST_POSTGRES_URL to an isolated local guardrail test database."
        )
    url = make_url(address)
    assert url.host in (None, "localhost", "127.0.0.1")
    assert url.query.get("host") in (None, "/var/run/postgresql")
    assert url.database.startswith("guardrail_")
    schema = "judge_" + uuid4().hex
    engine = create_engine(
        address,
        connect_args={"options": f"-c search_path={schema} -c lock_timeout=100ms"},
    )
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    for model in (
        DatabaseOrganization,
        DatabaseApplicationConfiguration,
        DatabaseSecretStorage,
    ):
        model.__table__.create(engine)
    sessions = sessionmaker(engine)
    org_id = uuid4()
    with sessions() as session:
        session.add(
            DatabaseOrganization(
                id=org_id, name="judge-test", created_at=datetime.now()
            )
        )
        ModelProviderRepository(session).set_model_provider_credentials(
            ModelProvider.OPENAI, api_key=SecretStr("first-local-credential")
        )

    @contextmanager
    def session_context():
        with sessions() as session:
            yield session

    monkeypatch.setattr(configuration_service, "db_session_context", session_context)
    monkeypatch.setenv("OPENAI_CONFIG_FILE", str(tmp_path / "absent.env"))
    try:
        yield sessions, org_id
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_default_save_vs_provider_delete_is_serialized(postgres_store):
    sessions, _ = postgres_store
    selection = GuardrailLLMConfiguration(provider=ModelProvider.OPENAI, model="gpt-4o")
    with sessions() as save, sessions() as delete:
        assert save.connection().connection is not delete.connection().connection
        lock_guardrail_configuration(save)
        GuardrailConfigurationRepository(save).write(selection)
        with pytest.raises(OperationalError, match="lock timeout"):
            ModelProviderRepository(delete).delete_model_provider_credentials(
                ModelProvider.OPENAI
            )
        delete.rollback()
        save.commit()
        ModelProviderRepository(delete).delete_model_provider_credentials(
            ModelProvider.OPENAI
        )
        assert GuardrailConfigurationRepository(delete).read() == (
            selection,
            "needs_configuration",
        )


def test_active_rotation_permission_rechecked_under_lock(postgres_store):
    sessions, _ = postgres_store
    with sessions() as save, sessions() as rotate:
        assert GuardrailConfigurationRepository(rotate).read()[0] is None
        lock_guardrail_configuration(save)
        GuardrailConfigurationRepository(save).write(
            GuardrailLLMConfiguration(provider=ModelProvider.OPENAI, model="gpt-4o")
        )
        with pytest.raises(OperationalError, match="lock timeout"):
            GuardrailConfigurationRepository(rotate).authorize_provider_mutation(
                ModelProvider.OPENAI, {TASK_ADMIN}
            )
        rotate.rollback()
        save.commit()
        with pytest.raises(HTTPException) as rejected:
            GuardrailConfigurationRepository(rotate).authorize_provider_mutation(
                ModelProvider.OPENAI, {TASK_ADMIN}
            )
        assert rejected.value.status_code == 403
        GuardrailConfigurationRepository(rotate).authorize_provider_mutation(
            ModelProvider.OPENAI, {ORG_ADMIN}
        )
        ModelProviderRepository(rotate).set_model_provider_credentials(
            ModelProvider.OPENAI, api_key=SecretStr("rotated-local-credential")
        )


def test_snapshot_reads_consistent_config_and_credentials(postgres_store):
    sessions, org_id = postgres_store
    with sessions() as session:
        GuardrailConfigurationRepository(session).write(
            GuardrailLLMConfiguration(provider=ModelProvider.OPENAI, model="gpt-4o")
        )
        session.commit()
    before = configuration_service.capture_judge_context(org_id)
    after = None
    try:
        with sessions() as rotate:
            lock_guardrail_configuration(rotate)
            secret = rotate.query(DatabaseSecretStorage).one()
            secret.value = {"api_key": "rotated-local-credential"}
            GuardrailConfigurationRepository(rotate).write(
                GuardrailLLMConfiguration(
                    provider=ModelProvider.OPENAI, model="gpt-4.1"
                )
            )
            assert (
                configuration_service.capture_judge_context(org_id).error
                == CONFIGURATION_UNAVAILABLE
            )
            rotate.commit()
        after = configuration_service.capture_judge_context(org_id)
        assert before.model == "gpt-4o"
        assert before.handle.client.api_key == "first-local-credential"
        assert after.model == "gpt-4.1"
        assert after.handle.client.api_key == "rotated-local-credential"
    finally:
        before.close()
        if after is not None:
            after.close()
