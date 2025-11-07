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
    DatabaseRagSearchSettingConfiguration,
    DatabaseRagSearchSettingConfigurationVersion,
)
from schemas.enums import (
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
)
from schemas.internal_schemas import (
    ApiKeyRagProviderSecretValue,
    RagProviderConfiguration,
    RagSearchSettingConfiguration,
    RagSearchSettingConfigurationVersion,
)
from schemas.request_schemas import (
    ApiKeyRagAuthenticationConfigUpdateRequest,
    RagProviderConfigurationUpdateRequest,
    RagSearchSettingConfigurationUpdateRequest,
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
        rag_setting_config: RagSearchSettingConfiguration,
    ) -> None:
        """Create a new RAG setting configuration"""
        db_config = rag_setting_config._to_database_model()
        self.db_session.add(db_config)
        self.db_session.commit()

    def _get_db_rag_setting_config(
        self,
        setting_config_id: UUID,
    ) -> DatabaseRagSearchSettingConfiguration:
        db_config = (
            self.db_session.query(DatabaseRagSearchSettingConfiguration)
            .filter(DatabaseRagSearchSettingConfiguration.id == setting_config_id)
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
    ) -> RagSearchSettingConfiguration:
        """Get a RAG provider configuration by ID with polymorphic loading"""
        db_config = self._get_db_rag_setting_config(config_id)
        return RagSearchSettingConfiguration._from_database_model(db_config)

    def delete_rag_setting_configuration(self, config_id: UUID) -> None:
        """Delete a RAG setting configuration"""
        db_config = self._get_db_rag_setting_config(config_id)
        self.db_session.delete(db_config)
        self.db_session.commit()

    def update_rag_provider_setting_configuration(
        self,
        config_id: UUID,
        update_config: RagSearchSettingConfigurationUpdateRequest,
    ) -> None:
        """Update a RAG provider setting configuration"""
        db_setting_config = self._get_db_rag_setting_config(config_id)

        if update_config.name:
            db_setting_config.name = update_config.name
        if update_config.description is not None:
            db_setting_config.description = update_config.description
        if update_config.rag_provider_id:
            # check rag provider exists - will raise 404 otherwise
            self._get_db_rag_provider_config(update_config.rag_provider_id)
            # set new field
            db_setting_config.rag_provider_id = update_config.rag_provider_id

        db_setting_config.updated_at = datetime.now()

        self.db_session.commit()

    def get_rag_search_setting_configurations_by_task(
        self,
        task_id: str,
        pagination_params: PaginationParameters,
        config_name: Optional[str],
        rag_provider_ids: Optional[list[UUID]],
    ) -> Tuple[List[RagSearchSettingConfiguration], int]:
        """Get RAG provider setting configurations for a task with pagination"""
        query = self.db_session.query(DatabaseRagSearchSettingConfiguration).filter(
            DatabaseRagSearchSettingConfiguration.task_id == task_id,
        )

        # apply filters
        if config_name:
            query = query.where(
                DatabaseRagSearchSettingConfiguration.name.ilike(f"%{config_name}%"),
            )
        if rag_provider_ids:
            query = query.where(
                DatabaseRagSearchSettingConfiguration.rag_provider_id.in_(
                    rag_provider_ids,
                ),
            )

        # apply sorting
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(
                desc(DatabaseRagSearchSettingConfiguration.updated_at),
            )
        elif pagination_params.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(
                asc(DatabaseRagSearchSettingConfiguration.updated_at),
            )

        total_count = query.count()

        # Apply pagination
        offset = pagination_params.page * pagination_params.page_size
        db_configs = query.offset(offset).limit(pagination_params.page_size).all()

        configs = [
            RagSearchSettingConfiguration._from_database_model(db_config)
            for db_config in db_configs
        ]
        return configs, total_count

    def create_rag_setting_configuration_version(
        self,
        rag_setting_version: RagSearchSettingConfigurationVersion,
    ) -> None:
        """Create a new RAG setting configuration version. Updates parent model metadata as needed."""
        # create new version
        db_version = rag_setting_version._to_database_model()

        # update parent model
        db_parent_config = self._get_db_rag_setting_config(
            rag_setting_version.setting_configuration_id,
        )
        db_parent_config.updated_at = db_version.created_at
        db_parent_config.latest_version_number = db_version.version_number

        # validate tags must be unique across versions - want to raise clean error instead of 5XX
        existing_tags = db_parent_config.all_possible_tags
        existing_tag_strings = {tag.tag for tag in existing_tags}
        for new_tag_db in db_version.tags:
            if new_tag_db.tag in existing_tag_strings:
                raise HTTPException(
                    status_code=404,
                    detail=f"RAG setting version tag {new_tag_db.tag} already exists for this configuration.",
                )
        # update all_possible_tags to include the new tags as well
        # reuse the tag DB objects from db_version to avoid creating duplicates
        tags_to_add = [tag_db for tag_db in db_version.tags]
        db_parent_config.all_possible_tags = existing_tags + tags_to_add

        # add objects to DB
        self.db_session.add(db_version)
        self.db_session.commit()

    def _get_db_rag_setting_config_version(
        self,
        setting_config_id: UUID,
        version_number: int,
    ) -> DatabaseRagSearchSettingConfigurationVersion:
        db_config = (
            self.db_session.query(DatabaseRagSearchSettingConfigurationVersion)
            .filter(
                DatabaseRagSearchSettingConfigurationVersion.setting_configuration_id
                == setting_config_id,
            )
            .filter(
                DatabaseRagSearchSettingConfigurationVersion.version_number
                == version_number,
            )
            .first()
        )

        if not db_config:
            raise HTTPException(
                status_code=404,
                detail="RAG setting configuration version not found",
            )
        return db_config

    def get_rag_setting_configuration_version(
        self,
        config_id: UUID,
        version_number: int,
    ) -> RagSearchSettingConfigurationVersion:
        """Get a RAG provider configuration version by ID and version number"""
        db_config = self._get_db_rag_setting_config_version(config_id, version_number)
        return RagSearchSettingConfigurationVersion._from_database_model(db_config)

    def _get_db_rag_setting_configuration_versions(
        self,
        setting_config_id: UUID,
    ) -> list[DatabaseRagSearchSettingConfigurationVersion]:
        """Gets list of RAG provider configuration versions by ID"""
        db_configs = (
            self.db_session.query(DatabaseRagSearchSettingConfigurationVersion)
            .filter(
                DatabaseRagSearchSettingConfigurationVersion.setting_configuration_id
                == setting_config_id,
            )
            .all()
        )

        if not db_configs:
            raise HTTPException(
                status_code=404,
                detail=f"No RAG setting configuration versions found for setting id {setting_config_id}",
            )
        return db_configs

    def soft_delete_rag_setting_configuration_version(
        self,
        config_id: UUID,
        version_number: int,
    ) -> None:
        db_version_config = self._get_db_rag_setting_config_version(
            config_id,
            version_number,
        )
        db_parent_config = self._get_db_rag_setting_config(config_id)
        db_version_config.deleted_at = datetime.now()

        # empty out all other fields in the version except for the PK fields and the created/updated fields
        db_version_config.settings = None
        # delete the tag records from the database and clear the relationship
        for tag in db_version_config.tags:
            self.db_session.delete(tag)
        db_version_config.tags = []

        # update db_parent_config updated_at time since one of its versions was affected
        db_parent_config.updated_at = datetime.now()

        self.db_session.commit()
