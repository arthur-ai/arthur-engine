import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from arthur_common.models.llm_model_providers import LLMBaseConfigSettings
from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Boolean,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base
from schemas.enums import EvalType

if TYPE_CHECKING:
    from db_models.task_models import DatabaseTask


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

    eval_type: Mapped[EvalType] = mapped_column(
        Enum(
            EvalType,
            values_callable=lambda e: [x.value for x in e],
            native_enum=False,
            create_constraint=False,
        ),
        nullable=False,
        server_default=EvalType.LLM_AS_A_JUDGE.value,
        default=EvalType.LLM_AS_A_JUDGE,
    )

    # LLM-only fields (None for ML eval types)
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model_provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    variables: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        server_default="[]",
        default=list,
    )

    # Eval configurations
    config: Mapped[Optional[LLMBaseConfigSettings]] = mapped_column(JSON, nullable=True)

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


class DatabaseContinuousEval(Base):
    __tablename__ = "continuous_evals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    task_id: Mapped[str] = mapped_column(String, nullable=False)

    # Discriminator — "llm_eval" or "ml_eval"
    eval_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default="llm_eval",
        default="llm_eval",
    )

    # Points to the eval (LLM or ML) in the llm_evals table. ML evals live in the
    # same table, so these are always populated regardless of eval_type.
    llm_eval_name: Mapped[str] = mapped_column(String, nullable=False)
    llm_eval_version: Mapped[int] = mapped_column(Integer, nullable=False)

    transform_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("trace_transforms.id", ondelete="RESTRICT"),
        nullable=False,
    )

    transform_variable_mapping: Mapped[List[dict[str, str]]] = mapped_column(
        JSON,
        nullable=False,
        server_default="[]",
        default=list,
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
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
