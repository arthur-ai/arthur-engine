import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base


class DatabaseLLMEval(Base):
    """Database model for storing llm evals associated with tasks"""

    __tablename__ = "llm_evals"

    # Composite primary key: task_id + name + version
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)

    # LLM Configuration
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_provider: Mapped[str] = mapped_column(String, nullable=False)

    # Prompt Content - stored as JSON for flexibility
    instructions: Mapped[str] = mapped_column(String, nullable=False)
    variables: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        server_default="[]",
        default=list,
    )

    # Eval configurations
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

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

    version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    @property
    def tags(self) -> List[str]:
        return [t.tag for t in self.version_tags]

    # Relationships
    task: Mapped["DatabaseTask"] = relationship(back_populates="llm_evals")
    version_tags: Mapped[List["DatabaseLLMEvalVersionTag"]] = relationship(
        back_populates="llm_eval",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabaseLLMEvalVersionTag(Base):
    __tablename__ = "llm_eval_version_tags"

    # Composite primary key: task_id + name + version
    task_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    tag: Mapped[str] = mapped_column(String, primary_key=True)

    llm_eval: Mapped["DatabaseLLMEval"] = relationship(
        back_populates="version_tags",
        lazy="select",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "name", "version"],
            ["llm_evals.task_id", "llm_evals.name", "llm_evals.version"],
            name="fk_llm_eval_version_tags_eval",
        ),
        UniqueConstraint("task_id", "name", "tag", name="uq_llm_eval_task_name_tag"),
    )


class DatabaseLLMEvalTransform(Base):
    __tablename__ = "llm_eval_transforms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4,
    )

    # llm eval composite primary key
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    llm_eval_name: Mapped[str] = mapped_column(String, nullable=False)
    llm_eval_version: Mapped[int] = mapped_column(Integer, nullable=False)

    transform_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("trace_transforms.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "llm_eval_name", "llm_eval_version"],
            ["llm_evals.task_id", "llm_evals.name", "llm_evals.version"],
            ondelete="CASCADE",
            name="fk_llm_eval_transforms_eval",
        ),
        UniqueConstraint(
            "task_id",
            "llm_eval_name",
            "transform_id",
            name="uq_llm_eval_transforms_task_id_name_transform_id",
        ),
    )
