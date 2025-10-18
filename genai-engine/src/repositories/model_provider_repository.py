import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from litellm import LiteLLM
from sqlalchemy.orm import Session
from typing import List

from clients.llm.llm_client import LLMClient
from db_models.secret_storage_models import DatabaseSecretStorage
from schemas.enums import ModelProvider, SecretType
from schemas.response_schemas import ModelProviderResponse

logger = logging.getLogger(__name__)


class ModelProviderRepository:
    API_KEY_SECRET_FIELD = "api_key"

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _format_creds_for_provider_secret(self, api_key: str) -> dict[str, str]:
        return {self.API_KEY_SECRET_FIELD: api_key}

    def _retrieve_api_key_from_secret(
        self, provider: ModelProvider, secret: dict
    ) -> str:
        key = secret.get(self.API_KEY_SECRET_FIELD)
        if not key:
            logger.warning(
                f"api_key not found in credential secret for provider {provider}"
            )
        return key

    def set_model_provider_credentials(
        self, provider: ModelProvider, api_key: str
    ) -> None:
        # first check if this provider already exists
        existing_provider = (
            self.db_session.query(DatabaseSecretStorage)
            .where(DatabaseSecretStorage.secret_type == SecretType.MODEL_PROVIDER)
            .where(DatabaseSecretStorage.name == provider)
            .first()
        )
        secret_data = self._format_creds_for_provider_secret(api_key)
        if existing_provider:
            existing_provider.value = secret_data
            existing_provider.updated_at = datetime.now()
        else:
            self.db_session.add(
                DatabaseSecretStorage(
                    id=str(uuid.uuid4()),
                    name=provider,
                    value=secret_data,
                    secret_type=SecretType.MODEL_PROVIDER,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
        self.db_session.commit()

    def delete_model_provider_credentials(
        self,
        provider: ModelProvider,
    ) -> None:
        providers = (
            self.db_session.query(DatabaseSecretStorage)
            .where(DatabaseSecretStorage.secret_type == SecretType.MODEL_PROVIDER)
            .where(DatabaseSecretStorage.name == provider)
            .all()
        )
        for provider in providers:
            self.db_session.delete(provider)
        self.db_session.commit()

    def get_model_provider_client(self, provider: ModelProvider) -> LLMClient:
        """Returns an authenticated LiteLLM client instance for the provider"""
        secret = (
            self.db_session.query(DatabaseSecretStorage)
            .where(DatabaseSecretStorage.secret_type == SecretType.MODEL_PROVIDER)
            .where(DatabaseSecretStorage.name == provider)
            .first()
        )
        if not secret:
            raise HTTPException(
                status_code=400,
                detail=f"model provider {provider} is not configured",
            )

        api_key = self._retrieve_api_key_from_secret(
            provider, secret.value  # type:ignore
        )
        return LLMClient(provider=provider, api_key=api_key)

    def list_model_providers(self) -> List[ModelProviderResponse]:
        enabled_providers_db_rows = (
            # only select name so we don't retrieve secret values
            self.db_session.query(DatabaseSecretStorage.name)
            .where(DatabaseSecretStorage.secret_type == SecretType.MODEL_PROVIDER)
            .all()
        )
        enabled_providers = set([p[0] for p in enabled_providers_db_rows])

        # construct responses based on if a secret is configured for the provider
        providers = []
        for provider in ModelProvider:
            providers.append(
                ModelProviderResponse(
                    provider=provider,  # type:ignore
                    enabled=provider in enabled_providers,
                )
            )

        return providers
