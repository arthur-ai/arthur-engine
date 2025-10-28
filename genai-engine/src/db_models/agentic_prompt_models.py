from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, SoftDeletedModel
from db_models.base import Base
from schemas.enums import ModelProvider

if TYPE_CHECKING:
    from db_models.task_models import DatabaseTask


class DatabaseAgenticPrompt(SoftDeletedModel, Base):
    """Database model for storing agentic prompts associated with tasks"""

    __tablename__ = "agentic_prompts"

    # Composite primary key: task_id + name + version
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # LLM Configuration
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_provider: Mapped[ModelProvider] = mapped_column(String, nullable=False)

    # Prompt Content - stored as JSON for flexibility
    messages: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    tools: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # prompt configurations
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="agentic_prompts")
