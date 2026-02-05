from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    event,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base

if TYPE_CHECKING:
    from db_models.task_models import DatabaseTask


class DatabaseAgentPollingData(Base):
    """
    Database model for the registered agent polling system
    """

    __tablename__ = "agent_polling_data"

    # Table constraints
    __table_args__ = (
        # Unique constraint: only one row per GCP resource_id
        Index(
            "uq_gcp_resource_id",
            text("(gcp_credentials->>'resource_id')"),
            unique=True,
            postgresql_where=text(
                "provider = 'gcp' AND gcp_credentials->>'resource_id' IS NOT NULL",
            ),
        ),
        # Check constraint: gcp_credentials must be non-null when provider is 'gcp'
        CheckConstraint(
            "provider != 'gcp' OR gcp_credentials IS NOT NULL",
            name="ck_gcp_credentials_required",
        ),
        # Check constraint: gcp_credentials must contain project_id, region, and resource_id
        CheckConstraint(
            """provider != 'gcp' OR (
                gcp_credentials ? 'project_id' AND
                gcp_credentials ? 'region' AND
                gcp_credentials ? 'resource_id' AND
                gcp_credentials->>'project_id' IS NOT NULL AND
                gcp_credentials->>'region' IS NOT NULL AND
                gcp_credentials->>'resource_id' IS NOT NULL
            )""",
            name="ck_gcp_credentials_fields",
        ),
    )

    # Primary identifiers
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String, nullable=False)

    # project id, resource id and region
    gcp_credentials: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(String, nullable=False)
    failed_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
        index=True,
    )
    last_fetched: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        default=None,
        nullable=True,
    )

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="agent_polling_data")


# Event listener to remove PostgreSQL-specific constraint from SQLite
@event.listens_for(DatabaseAgentPollingData.__table__, "before_create")
def _remove_postgres_constraint_for_sqlite(
    target: Any,
    connection: Any,
    **_kw: Any,
) -> None:
    """Remove the JSONB check constraint for SQLite compatibility"""
    if connection.dialect.name == "sqlite":
        # Remove the ck_gcp_credentials_fields constraint which uses PostgreSQL JSONB operators
        target.constraints = {
            c
            for c in target.constraints
            if not (
                isinstance(c, CheckConstraint) and c.name == "ck_gcp_credentials_fields"
            )
        }
