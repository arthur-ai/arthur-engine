import uuid
from datetime import datetime
from typing import Union

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    ForeignKey,
    String,
)
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
