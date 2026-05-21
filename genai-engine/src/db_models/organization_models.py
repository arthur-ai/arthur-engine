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
    #
    # Python-side `default`s are used for `id` and `created_at` so SQLAlchemy
    # supplies the values on every ORM insert. The Postgres migration also
    # sets server-side defaults (`gen_random_uuid()`, `now()`) — both for
    # any raw-SQL insert paths and so the column has a sensible default in
    # the schema; ORM inserts never fall through to them in practice.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.now,
    )

    __table_args__ = (
        # Partial unique index: only one row with is_system=TRUE is allowed.
        # Without dialect-specific `where` clauses for *both* Postgres and
        # SQLite, SQLite treats the index as unconditional and rejects every
        # row after the first is_system=FALSE — which breaks tenant signup
        # in unit tests that hit the real test DB.
        Index(
            "uq_organizations_is_system_true",
            "is_system",
            unique=True,
            postgresql_where=text("is_system = TRUE"),
            sqlite_where=text("is_system = TRUE"),
        ),
    )
