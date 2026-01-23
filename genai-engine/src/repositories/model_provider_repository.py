import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy.orm import Session
from starlette.status import HTTP_400_BAD_REQUEST

from clients.llm.llm_client import LLMClient
from db_models.secret_storage_models import DatabaseSecretStorage
from schemas.enums import SecretType
from schemas.internal_schemas import AwsBedrockCredentials, GCPServiceAccountCredentials
from schemas.request_schemas import PutModelProviderCredentials
from schemas.response_schemas import ModelProviderResponse

logger = logging.getLogger(__name__)


class ModelProviderRepository:
    API_KEY_SECRET_FIELD = "api_key"
    API_BASE_SECRET_FIELD = "api_base"

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _format_creds_for_provider_secret(
        self,
        api_key: Optional[SecretStr] = None,
        api_base: Optional[SecretStr] = None,
    ) -> dict[str, dict[str, str]]:
        creds = {}
        if api_key:
            creds[self.API_KEY_SECRET_FIELD] = {
                self.API_KEY_SECRET_FIELD: api_key.get_secret_value(),
            }
        if api_base:
            creds[self.API_BASE_SECRET_FIELD] = {
                self.API_BASE_SECRET_FIELD: api_base.get_secret_value(),
            }
        return creds

    def _format_creds_for_vertex_credentials(
        self,
        vertex_credentials: GCPServiceAccountCredentials,
    ) -> dict[str, str]:
        return vertex_credentials.to_sensitive_dict()

    def _format_creds_for_aws_bedrock_credentials(
        self,
        aws_bedrock_credentials: AwsBedrockCredentials,
    ) -> dict[str, str]:
        return aws_bedrock_credentials.to_sensitive_dict()

    def _retrieve_api_key_from_secret(
        self,
        provider: ModelProvider,
        secret: dict[str, Any],
    ) -> str:
        key: str | None = secret.get(self.API_KEY_SECRET_FIELD)
        if not key:
            logger.warning(
                f"api_key not found in credential secret for provider {provider}",
            )
            return ""
        return key

    def _retrieve_vertex_credentials_from_secret(
        self,
        secret_storage: DatabaseSecretStorage,
    ) -> Dict[str, str] | None:
        """Retrieve and reconstruct GCPServiceAccountCredentials from the encrypted storage."""
        if not secret_storage.vertex_credentials:
            return None

        creds_dict = secret_storage.vertex_credentials

        return {
            "type": creds_dict.get("type", ""),
            "project_id": creds_dict.get("project_id", ""),
            "private_key_id": creds_dict.get("private_key_id", ""),
            "private_key": creds_dict.get("private_key", ""),
            "client_email": creds_dict.get("client_email", ""),
            "client_id": creds_dict.get("client_id", ""),
            "auth_uri": creds_dict.get("auth_uri", ""),
            "token_uri": creds_dict.get("token_uri", ""),
            "auth_provider_x509_cert_url": creds_dict.get(
                "auth_provider_x509_cert_url",
                "",
            ),
            "client_x509_cert_url": creds_dict.get("client_x509_cert_url", ""),
            "universe_domain": creds_dict.get("universe_domain", ""),
        }

    def _retrieve_aws_bedrock_credentials_from_secret(
        self,
        secret_storage: DatabaseSecretStorage,
    ) -> Dict[str, str] | None:
        """Retrieve and reconstruct AwsBedrockCredentials from the encrypted storage."""
        if not secret_storage.aws_bedrock_credentials:
            return None

        creds_dict = secret_storage.aws_bedrock_credentials

        return {
            "aws_access_key_id": creds_dict.get("aws_access_key_id", ""),
            "aws_secret_access_key": creds_dict.get("aws_secret_access_key", ""),
            "aws_bedrock_runtime_endpoint": creds_dict.get(
                "aws_bedrock_runtime_endpoint",
                "",
            ),
            "aws_role_name": creds_dict.get("aws_role_name", ""),
            "aws_session_name": creds_dict.get("aws_session_name", ""),
        }

    def validate_model_provider_credentials(
        self,
        provider: ModelProvider,
        provider_credentials: PutModelProviderCredentials,
    ) -> None:
        has_aws_access_key_id = provider_credentials.aws_access_key_id is not None
        has_aws_secret_access_key = (
            provider_credentials.aws_secret_access_key is not None
        )
        has_credentials_file = provider_credentials.credentials_file is not None

        if provider == ModelProvider.VERTEX_AI:
            if provider_credentials.api_key is not None:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="API key cannot be used for this provider",
                )
            if has_credentials_file == False:
                logger.warning(
                    "No credentials file provided for Vertex AI. Falling back to using default credentials. If there is no attached service account or cli authenticated gcp account, calls to vertex ai will fail",
                )
        elif provider == ModelProvider.BEDROCK:
            if (not has_aws_access_key_id and has_aws_secret_access_key) or (
                has_aws_access_key_id and not has_aws_secret_access_key
            ):
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="aws_access_key_id and aws_secret_access_key must be provided together",
                )
            elif (
                provider_credentials.api_key is None
                and not has_aws_access_key_id
                and not has_aws_secret_access_key
            ):
                logger.warning(
                    "No api key or aws credentials provided for Bedrock. Falling back to using default credentials. If you don't have the proper configurations in this environment, calls to bedrock will fail",
                )
        elif provider == ModelProvider.VLLM:
            if provider_credentials.api_base is None:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="api_base is required for VLLM hosted models",
                )
        elif provider_credentials.api_key is None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="API key is required for this provider",
            )

    def set_model_provider_credentials(
        self,
        provider: ModelProvider,
        api_key: SecretStr = None,
        project_id: str = None,
        region: str = None,
        api_base: SecretStr = None,
        vertex_credentials: GCPServiceAccountCredentials = None,
        aws_bedrock_credentials: AwsBedrockCredentials = None,
    ) -> None:
        # first check if this provider already exists
        existing_provider = (
            self.db_session.query(DatabaseSecretStorage)
            .where(DatabaseSecretStorage.secret_type == SecretType.MODEL_PROVIDER)
            .where(DatabaseSecretStorage.name == provider)
            .first()
        )
        secret_data = self._format_creds_for_provider_secret(api_key, api_base)

        vertex_credentials_data = None
        if vertex_credentials:
            vertex_credentials_data = self._format_creds_for_vertex_credentials(
                vertex_credentials,
            )

        aws_bedrock_credentials_data = None
        if aws_bedrock_credentials:
            aws_bedrock_credentials_data = (
                self._format_creds_for_aws_bedrock_credentials(aws_bedrock_credentials)
            )

        if existing_provider:
            existing_provider.value = secret_data.get(self.API_KEY_SECRET_FIELD)
            existing_provider.project_id = project_id
            existing_provider.region = region
            existing_provider.api_base = secret_data.get(self.API_BASE_SECRET_FIELD)
            existing_provider.vertex_credentials = vertex_credentials_data
            existing_provider.aws_bedrock_credentials = aws_bedrock_credentials_data
            existing_provider.updated_at = datetime.now()
        else:
            self.db_session.add(
                DatabaseSecretStorage(
                    id=str(uuid.uuid4()),
                    name=provider,
                    value=secret_data.get(self.API_KEY_SECRET_FIELD),
                    secret_type=SecretType.MODEL_PROVIDER,
                    project_id=project_id,
                    region=region,
                    api_base=secret_data.get(self.API_BASE_SECRET_FIELD),
                    vertex_credentials=vertex_credentials_data,
                    aws_bedrock_credentials=aws_bedrock_credentials_data,
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

        api_key = None
        if secret.value is not None:
            api_key = self._retrieve_api_key_from_secret(provider, secret.value)

        vertex_credentials = self._retrieve_vertex_credentials_from_secret(secret)
        aws_bedrock_credentials = self._retrieve_aws_bedrock_credentials_from_secret(
            secret,
        )

        api_base = None
        if secret.api_base:
            api_base = secret.api_base.get(self.API_BASE_SECRET_FIELD)

        return LLMClient(
            provider=provider,
            api_key=api_key,
            project_id=secret.project_id,
            region=secret.region,
            api_base=api_base,
            vertex_credentials=vertex_credentials,
            aws_bedrock_credentials=aws_bedrock_credentials,
        )

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
