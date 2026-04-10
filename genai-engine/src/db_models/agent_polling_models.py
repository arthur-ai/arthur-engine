from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base

if TYPE_CHECKING:
    from db_models.task_models import DatabaseTask


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
