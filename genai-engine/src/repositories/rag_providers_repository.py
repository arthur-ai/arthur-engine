import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from db_models.rag_provider_models import (
    DatabaseApiKeyRagProviderConfiguration,
    DatabaseRagProviderConfiguration,
    DatabaseRagSettingConfiguration,
)
from schemas.enums import (
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
)
from schemas.internal_schemas import (
    ApiKeyRagProviderSecretValue,
    RagProviderConfiguration,
    RagSettingConfiguration,
)
from schemas.request_schemas import (
    ApiKeyRagAuthenticationConfigUpdateRequest,
    RagProviderConfigurationUpdateRequest,
    RagSettingConfigurationUpdateRequest,
)

logger = logging.getLogger(__name__)


class RagProvidersRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_rag_provider_configuration(
        self,
        rag_provider_config: RagProviderConfiguration,
    ) -> None:
        """Create a new RAG provider configuration with polymorphic support"""
        db_config = rag_provider_config._to_database_model()
        self.db_session.add(db_config)
        self.db_session.commit()

    def _get_db_rag_provider_config(
        self,
        config_id: UUID,
    ) -> DatabaseRagProviderConfiguration:
        db_config = (
            self.db_session.query(DatabaseRagProviderConfiguration)
            .filter(DatabaseRagProviderConfiguration.id == config_id)
            .first()
        )

        if not db_config:
            raise HTTPException(
                status_code=404,
                detail="RAG provider configuration not found",
            )
        return db_config

    def get_rag_provider_configuration(
        self,
        config_id: UUID,
    ) -> RagProviderConfiguration:
        """Get a RAG provider configuration by ID with polymorphic loading"""
        db_config = self._get_db_rag_provider_config(config_id)
        return RagProviderConfiguration._from_database_model(db_config)

    def get_rag_provider_configurations_by_task(
        self,
        task_id: str,
        pagination_params: PaginationParameters,
        config_name: Optional[str],
        authentication_method: Optional[RagProviderAuthenticationMethodEnum],
        rag_provider_name: Optional[RagAPIKeyAuthenticationProviderEnum],
    ) -> Tuple[List[RagProviderConfiguration], int]:
        """Get RAG provider configurations for a task with pagination"""
        query = self.db_session.query(DatabaseRagProviderConfiguration).filter(
            DatabaseRagProviderConfiguration.task_id == task_id,
        )

        # apply filters
        if config_name:
            query = query.where(
                DatabaseRagProviderConfiguration.name.ilike(f"%{config_name}%"),
            )
        if authentication_method:
            query = query.where(
                DatabaseRagProviderConfiguration.authentication_method
                == authentication_method,
            )
        if rag_provider_name:
            query = query.where(
                DatabaseApiKeyRagProviderConfiguration.rag_provider
                == rag_provider_name,
            )

        # apply sorting
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseRagProviderConfiguration.updated_at))
        elif pagination_params.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseRagProviderConfiguration.updated_at))

        total_count = query.count()

        # Apply pagination
        offset = pagination_params.page * pagination_params.page_size
        db_configs = query.offset(offset).limit(pagination_params.page_size).all()

        configs = [
            RagProviderConfiguration._from_database_model(db_config)
            for db_config in db_configs
        ]
        return configs, total_count

    def update_rag_provider_configuration(
        self,
        config_id: UUID,
        update_config: RagProviderConfigurationUpdateRequest,
    ) -> None:
        """Update a RAG provider configuration"""
        db_provider = self._get_db_rag_provider_config(config_id)

        if update_config.name:
            db_provider.name = update_config.name
        if update_config.description is not None:
            db_provider.description = update_config.description
        if update_config.authentication_config is not None:
            if isinstance(
                update_config.authentication_config,
                ApiKeyRagAuthenticationConfigUpdateRequest,
            ):
                if update_config.authentication_config.api_key:
                    new_secret_value = ApiKeyRagProviderSecretValue(
                        api_key=update_config.authentication_config.api_key,
                    )
                    db_provider.api_key.value = new_secret_value.model_dump(mode="json")
                    db_provider.api_key.updated_at = datetime.now()
                if update_config.authentication_config.host_url:
                    db_provider.host_url = str(
                        update_config.authentication_config.host_url,
                    )
                if update_config.authentication_config.rag_provider:
                    db_provider.rag_provider = (
                        update_config.authentication_config.rag_provider
                    )
                if (
                    update_config.authentication_config.authentication_method
                    is not None
                ):
                    db_provider.authentication_method = (
                        update_config.authentication_config.authentication_method
                    )
            else:
                raise HTTPException(
                    status_code=404,
                    detail="RAG provider configuration update not supported for this config type.",
                )
        db_provider.updated_at = datetime.now()

        self.db_session.commit()

    def delete_rag_provider_configuration(self, config_id: UUID) -> None:
        """Delete a RAG provider configuration"""
        db_config = self._get_db_rag_provider_config(config_id)
        self.db_session.delete(db_config)
        self.db_session.commit()

    def create_rag_setting_configuration(
        self,
        rag_setting_config: RagSettingConfiguration,
    ) -> None:
        """Create a new RAG setting configuration"""
        db_config = rag_setting_config._to_database_model()
        self.db_session.add(db_config)
        self.db_session.commit()

    def _get_db_rag_setting_config(
        self,
        setting_config_id: UUID,
    ) -> DatabaseRagSettingConfiguration:
        db_config = (
            self.db_session.query(DatabaseRagSettingConfiguration)
            .filter(DatabaseRagSettingConfiguration.id == setting_config_id)
            .first()
        )

        if not db_config:
            raise HTTPException(
                status_code=404,
                detail="RAG setting configuration not found",
            )
        return db_config

    def get_rag_setting_configuration(
        self,
        config_id: UUID,
    ) -> RagSettingConfiguration:
        """Get a RAG provider configuration by ID with polymorphic loading"""
        db_config = self._get_db_rag_setting_config(config_id)
        return RagSettingConfiguration._from_database_model(db_config)

    def delete_rag_setting_configuration(self, config_id: UUID) -> None:
        """Delete a RAG setting configuration"""
        db_config = self._get_db_rag_setting_config(config_id)
        self.db_session.delete(db_config)
        self.db_session.commit()

    def update_rag_provider_setting_configuration(
        self,
        config_id: UUID,
        update_config: RagSettingConfigurationUpdateRequest,
    ) -> None:
        """Update a RAG provider setting configuration"""
        db_setting_config = self._get_db_rag_setting_config(config_id)

        if update_config.name:
            db_setting_config.name = update_config.name
        if update_config.description is not None:
            db_setting_config.description = update_config.description

        db_setting_config.updated_at = datetime.now()

        self.db_session.commit()

    def get_rag_provider_setting_configurations_by_task(
        self,
        task_id: str,
        pagination_params: PaginationParameters,
        config_name: Optional[str],
    ) -> Tuple[List[RagSettingConfiguration], int]:
        """Get RAG provider setting configurations for a task with pagination"""
        query = self.db_session.query(DatabaseRagSettingConfiguration).filter(
            DatabaseRagSettingConfiguration.task_id == task_id,
        )

        # apply filters
        if config_name:
            query = query.where(
                DatabaseRagSettingConfiguration.name.ilike(f"%{config_name}%"),
            )

        # apply sorting
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseRagSettingConfiguration.updated_at))
        elif pagination_params.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseRagSettingConfiguration.updated_at))

        total_count = query.count()

        # Apply pagination
        offset = pagination_params.page * pagination_params.page_size
        db_configs = query.offset(offset).limit(pagination_params.page_size).all()

        configs = [
            RagSettingConfiguration._from_database_model(db_config)
            for db_config in db_configs
        ]
        return configs, total_count
