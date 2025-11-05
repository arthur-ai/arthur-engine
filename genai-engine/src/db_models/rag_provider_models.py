import uuid
from datetime import datetime
from typing import Any, List, Optional, Union

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base
from schemas.enums import (
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
)


class DatabaseRagProviderConfiguration(Base):
    """Base polymorphic model for RAG provider configurations"""

    __tablename__ = "rag_provider_configurations"
    __mapper_args__ = {
        "polymorphic_on": "authentication_method",
    }

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    authentication_method: Mapped[RagProviderAuthenticationMethodEnum] = mapped_column(
        String,
    )
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    # relationship to settings configurations - needed for passive deletes to work
    search_setting_configurations: Mapped[
        List["DatabaseRagSearchSettingConfiguration"]
    ] = relationship(
        "DatabaseRagSearchSettingConfiguration",
        back_populates="rag_provider",
    )


class DatabaseApiKeyRagProviderConfiguration(DatabaseRagProviderConfiguration):
    """API Key authentication configuration for RAG providers"""

    __mapper_args__ = {
        "polymorphic_identity": RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
    }
    api_key_secret_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("secret_storage.id"),
        index=True,
        nullable=True,
        use_existing_column=True,
    )
    api_key: Mapped["DatabaseSecretStorage"] = relationship(
        lazy="joined",
        cascade="all,delete",
    )
    host_url: Mapped[str] = mapped_column(
        String,
        nullable=True,
        use_existing_column=True,
    )
    rag_provider: Mapped[RagAPIKeyAuthenticationProviderEnum] = mapped_column(
        String,
        nullable=True,
        use_existing_column=True,
    )


DatabaseRagProviderAuthenticationConfigurationTypes = Union[
    DatabaseApiKeyRagProviderConfiguration
]


class DatabaseRagSearchSettingConfiguration(Base):
    __tablename__ = "rag_search_setting_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
    )
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        index=True,
    )
    rag_provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("rag_provider_configurations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    # relationship to the provider configuration - needed for passive deletes to work
    rag_provider: Mapped[Optional["DatabaseRagProviderConfiguration"]] = relationship(
        "DatabaseRagProviderConfiguration",
        back_populates="search_setting_configurations",
    )
    all_possible_tags: Mapped[Optional[list[str]]] = mapped_column(
        postgresql.JSON,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    latest_version_number: Mapped[int] = mapped_column(Integer)
    latest_version: Mapped["DatabaseRagSearchSettingConfigurationVersion"] = (
        relationship(
            lazy="joined",
            primaryjoin="and_("
            "DatabaseRagSearchSettingConfigurationVersion.setting_configuration_id == DatabaseRagSearchSettingConfiguration.id, "
            "DatabaseRagSearchSettingConfigurationVersion.version_number == DatabaseRagSearchSettingConfiguration.latest_version_number"
            ")",
            foreign_keys="[DatabaseRagSearchSettingConfigurationVersion.setting_configuration_id]",
        )
    )
    all_versions: Mapped[List["DatabaseRagSearchSettingConfigurationVersion"]] = (
        relationship(
            cascade="all,delete",
            foreign_keys="[DatabaseRagSearchSettingConfigurationVersion.setting_configuration_id]",
            overlaps="latest_version",
        )
    )  # relationship exists to cascade delete
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class DatabaseRagSearchSettingConfigurationVersion(Base):
    """Base model for RAG setting configuration versions

    We won't use polymorphic support for these classes because the number of columns would be likely to get large—
    the configurations will be polymorphic on both the search kind and the RAG provider—
    instead we'll store the settings as JSON. This should be sufficient because we're likely to never need to filter on
    specific setting configurations.
    """

    __tablename__ = "rag_search_setting_configuration_versions"

    setting_configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("rag_search_setting_configurations.id"),
        primary_key=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    settings: Mapped[dict[str, Any]] = mapped_column(postgresql.JSON)
    tags: Mapped[Optional[list[str]]] = mapped_column(postgresql.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
