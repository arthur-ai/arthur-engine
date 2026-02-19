from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base

if TYPE_CHECKING:
    from db_models.task_models import DatabaseTask


class DatabaseAgentPollingData(Base):
    """
    Database model for the registered agent polling system.

    DEPRECATED: Being replaced by DatabaseTaskPollingState.
    Kept temporarily for migration support.
    """

    __tablename__ = "agent_polling_data"

    # Primary identifiers
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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


class DatabaseTaskPollingState(Base):
    """
    Simplified polling state for agent tasks.

    Tracks only when a task was last successfully polled.
    No error state — polling always continues. Errors are logged for
    observability but do not block future polls.
    """

    __tablename__ = "task_polling_state"

    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_fetched: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        default=None,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="task_polling_state")
