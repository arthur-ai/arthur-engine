from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base

if TYPE_CHECKING:
    from db_models.agentic_experiment_models import DatabaseAgenticExperiment
    from db_models.dataset_models import DatabaseDataset


class DatabaseAgenticNotebook(Base):
    """
    Database model for agentic notebooks - draft agentic experiment configurations.

    An agentic notebook represents a working draft of an agentic experiment configuration associated with a task.
    It has the same structure as AgenticExperiment, but fields can be null/incomplete.
    When the notebook is "run", it creates an AgenticExperiment from the notebook's state.
    """

    __tablename__ = "agentic_notebooks"

    # Primary identifiers
    id: Mapped[str] = mapped_column(String, primary_key=True)
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

    # Draft experiment state (mirrors AgenticExperiment but nullable)
    # For agentic experiments
    http_template: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    template_variable_mapping: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    # Shared fields
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID, nullable=True)
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
    dataset: Mapped[Optional["DatabaseDataset"]] = relationship(
        "DatabaseDataset",
        primaryjoin="DatabaseAgenticNotebook.dataset_id == foreign(DatabaseDataset.id)",
        lazy="select",
        viewonly=True,
    )
    experiments: Mapped[List["DatabaseAgenticExperiment"]] = relationship(
        back_populates="notebook",
        lazy="select",
        order_by="desc(DatabaseAgenticExperiment.created_at)",
    )
