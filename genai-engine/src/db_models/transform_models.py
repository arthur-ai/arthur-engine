import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    ForeignKey,
    String,
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
