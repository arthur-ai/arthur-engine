import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base

if TYPE_CHECKING:
    pass


class DatabaseTraceTransform(Base):
    __tablename__ = "trace_transforms"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    definition: Mapped[Dict[str, Any]] = mapped_column(postgresql.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)


class DatabaseTraceTransformVersion(Base):
    """Immutable version snapshot for a trace transform configuration."""

    __tablename__ = "transform_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    transform_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("trace_transforms.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        postgresql.JSON, nullable=False
    )
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "transform_id",
            "version_number",
            name="uq_transform_version_number",
        ),
    )
