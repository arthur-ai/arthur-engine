import logging
import uuid
from datetime import datetime
from typing import Any, List

from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient
from db_models.secret_storage_models import DatabaseSecretStorage
from schemas.enums import ModelProvider, SecretType
from schemas.response_schemas import ModelProviderResponse

logger = logging.getLogger(__name__)


class ModelProviderRepository:
    API_KEY_SECRET_FIELD = "api_key"
    PROJECT_ID_SECRET_FIELD = "project_id"
    REGION_SECRET_FIELD = "region"

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _format_creds_for_provider_secret(
        self,
        provider: ModelProvider,
        api_key: SecretStr | None = None,
        project_id: str | None = None,
        region: str | None = None,
    ) -> dict[str, str]:
        if provider == ModelProvider.VERTEX_AI:
            if not project_id or not region:
                raise ValueError("project_id and region are required for Vertex AI")
            return {
                self.PROJECT_ID_SECRET_FIELD: project_id,
                self.REGION_SECRET_FIELD: region,
            }
        else:
            if not api_key:
                raise ValueError("api_key is required for non-Vertex AI providers")
            return {self.API_KEY_SECRET_FIELD: api_key.get_secret_value()}

    def _retrieve_credentials_from_secret(
        self,
        provider: ModelProvider,
        secret: dict[str, Any],
    ) -> dict[str, str]:
        """Retrieve credentials from secret storage based on provider type"""
        if provider == ModelProvider.VERTEX_AI:
            project_id = secret.get(self.PROJECT_ID_SECRET_FIELD)
            region = secret.get(self.REGION_SECRET_FIELD)
            if not project_id or not region:
                logger.warning(
                    f"project_id or region not found in credential secret for provider {provider}",
                )
                return {"project_id": "", "region": ""}
            return {"project_id": project_id, "region": region}
        else:
            key = secret.get(self.API_KEY_SECRET_FIELD)
            if not key:
                logger.warning(
                    f"api_key not found in credential secret for provider {provider}",
                )
                return {"api_key": ""}
            return {"api_key": key}

    def _retrieve_api_key_from_secret(
        self,
        provider: ModelProvider,
        secret: dict[str, Any],
    ) -> str:
        """Legacy method for backward compatibility - retrieves api_key for non-Vertex AI providers"""
        if provider == ModelProvider.VERTEX_AI:
            raise ValueError("Cannot retrieve api_key for Vertex AI provider")
        key: str | None = secret.get(self.API_KEY_SECRET_FIELD)
        if not key:
            logger.warning(
                f"api_key not found in credential secret for provider {provider}",
            )
            return ""
        return key

    def set_model_provider_credentials(
        self,
        provider: ModelProvider,
        api_key: SecretStr | None = None,
        project_id: str | None = None,
        region: str | None = None,
    ) -> None:
        # first check if this provider already exists
        existing_provider = (
            self.db_session.query(DatabaseSecretStorage)
            .where(DatabaseSecretStorage.secret_type == SecretType.MODEL_PROVIDER)
            .where(DatabaseSecretStorage.name == provider)
            .first()
        )
        secret_data = self._format_creds_for_provider_secret(
            provider=provider,
            api_key=api_key,
            project_id=project_id,
            region=region,
        )
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
                ),
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
        for provider_db in providers:
            self.db_session.delete(provider_db)
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

        credentials = self._retrieve_credentials_from_secret(provider, secret.value)

        if provider == ModelProvider.VERTEX_AI:
            project_id = credentials.get("project_id", "")
            region = credentials.get("region", "")
            if not project_id or not region:
                raise HTTPException(
                    status_code=400,
                    detail=f"Vertex AI provider is not properly configured. Missing project_id or region.",
                )
            return LLMClient(
                provider=provider,
                api_key="",  # Not used for Vertex AI
                project_id=project_id,
                region=region,
            )
        else:
            api_key = credentials.get("api_key", "")
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail=f"Provider {provider} is not properly configured. Missing api_key.",
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
                    provider=provider,
                    enabled=provider in enabled_providers,
                ),
            )

        return providers

    def list_models_for_provider(self, provider: ModelProvider) -> List[str]:
        client = self.get_model_provider_client(provider)
        return client.get_available_models()
