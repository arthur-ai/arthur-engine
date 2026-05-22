import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base


class DatabaseOrganization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        # Partial unique index: only one row may have is_system=TRUE. The
        # `where` clause needs both dialect kwargs so the partial-index
        # semantic survives both Postgres (production) and SQLite (tests);
        # without `sqlite_where` SQLite treats the index as unconditional
        # and rejects every is_system=FALSE row after the first.
        Index(
            "uq_organizations_is_system_true",
            "is_system",
            unique=True,
            postgresql_where=text("is_system = TRUE"),
            sqlite_where=text("is_system = TRUE"),
        ),
    )
