from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base

if TYPE_CHECKING:
    from db_models.prompt_experiment_models import DatabasePromptExperiment


class DatabaseNotebook(Base):
    """
    Database model for notebooks - draft experiment configurations.

    A notebook represents a working draft of an experiment configuration associated with a task.
    It has the same structure as PromptExperiment, but fields can be null/incomplete.
    When the notebook is "run", it creates a PromptExperiment from the notebook's state.
    """

    __tablename__ = "notebooks"

    # Primary identifiers
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic metadata
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    # Draft experiment state (mirrors PromptExperiment but nullable)
    prompt_configs: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    prompt_variable_mapping: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    dataset_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dataset_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dataset_row_filter: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    eval_configs: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    experiments: Mapped[List["DatabasePromptExperiment"]] = relationship(
        back_populates="notebook",
        lazy="select",
        order_by="desc(DatabasePromptExperiment.created_at)",
    )
