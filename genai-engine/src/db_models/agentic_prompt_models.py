from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base


class DatabaseAgenticPrompt(Base):
    """Database model for storing agentic prompts associated with tasks"""

    __tablename__ = "agentic_prompts"

    # Composite primary key: task_id + name
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

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
        default=None,
    )

    # LLM Configuration
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_provider: Mapped[str] = mapped_column(String, nullable=False)

    # Prompt Content - stored as JSON for flexibility
    messages: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    tools: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    # prompt configurations
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Ensure name is unique within each task
    __table_args__ = (
        UniqueConstraint("task_id", "name", "version", name="uq_task_prompt_version"),
    )

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="agentic_prompts")
