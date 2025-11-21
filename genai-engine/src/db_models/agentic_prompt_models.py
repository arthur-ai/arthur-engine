from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, SoftDeletedModel
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
    variables: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        server_default="[]",
        default=list,
    )

    # prompt configurations
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    @property
    def tags(self) -> List[str]:
        return [t.tag for t in self.version_tags]

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="agentic_prompts")
    version_tags: Mapped[List["DatabaseAgenticPromptVersionTag"]] = relationship(
        back_populates="agentic_prompt",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabaseAgenticPromptVersionTag(Base):
    __tablename__ = "agentic_prompt_version_tags"

    # Composite primary key: task_id + name + version + tag
    task_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    tag: Mapped[str] = mapped_column(String, primary_key=True)

    agentic_prompt: Mapped["DatabaseAgenticPrompt"] = relationship(
        back_populates="version_tags",
        lazy="select",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "name", "version"],
            [
                "agentic_prompts.task_id",
                "agentic_prompts.name",
                "agentic_prompts.version",
            ],
            name="fk_agentic_prompt_version_tags_prompt",
        ),
        UniqueConstraint(
            "task_id",
            "name",
            "tag",
            name="uq_agentic_prompt_task_name_tag",
        ),
    )
