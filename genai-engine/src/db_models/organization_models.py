import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base


class DatabaseOrganization(Base):
    __tablename__ = "organizations"

    # Use SQLAlchemy's cross-dialect `Uuid` type instead of postgresql.UUID
    # so the in-memory test DB (SQLite) round-trips UUIDs as strings.
    # On PostgreSQL the underlying column is still UUID; the migration
    # uses `sa.UUID()` which renders to the same column type.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index(
            "uq_organizations_is_system_true",
            "is_system",
            unique=True,
            postgresql_where=text("is_system = TRUE"),
        ),
    )
