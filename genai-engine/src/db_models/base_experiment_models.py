from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from db_models.base import Base
from schemas.base_experiment_schemas import ExperimentStatus, TestCaseStatus

# TYPE_CHECKING is False at runtime but True during static type checking.
# This avoids circular import errors (notebook_models imports this file)
# while still providing type hints for IDEs and mypy.
if TYPE_CHECKING:
    pass


class DatabaseBaseExperiment(Base):
    """Base database model for storing experiments associated with tasks.

    This abstract base class contains common fields shared across all experiment types
    (prompt experiments, RAG experiments, etc.). Subclasses should define their own
    __tablename__ and add type-specific fields.
    """

    __abstract__ = True

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign key to task
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign key to notebook (optional)
    notebook_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("notebooks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Basic experiment metadata
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[ExperimentStatus] = mapped_column(
        String,
        nullable=False,
        default=ExperimentStatus.QUEUED.value,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
        index=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
    )

    # Dataset reference
    dataset_id: Mapped[UUID] = mapped_column(PGUUID, nullable=False)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Dataset row filter (optional) stored as JSON
    # Structure: [{"column_name": str, "column_value": str}, ...]
    # Only rows matching ALL filter conditions (AND logic) are included in the experiment
    dataset_row_filter: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Eval configurations stored as JSON
    # Structure: [{"name": str, "version": str, "variable_mapping": [...]}, ...]
    eval_configs: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)

    # Summary statistics (denormalized for quick access)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Total cost across all test cases (string to maintain precision)
    total_cost: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Summary results stored as JSON (computed after experiment completes)
    # Structure varies by experiment type
    summary_results: Mapped[
        Optional[dict[str, list[dict[str, str | list[dict[str, str | int]]]]]]
    ] = mapped_column(JSON, nullable=True)

    # Relationships are defined in subclasses since they are type-specific
    # (notebook, test_cases, dataset)

    # Table args for composite foreign key
    # Subclasses should override __table_args__ to specify their own ForeignKeyConstraint
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "dataset_version"],
            ["dataset_versions.dataset_id", "dataset_versions.version_number"],
        ),
    )


class DatabaseBaseExperimentTestCase(Base):
    """Base database model for individual test case results within an experiment.

    This abstract base class contains common fields shared across all experiment test case types.
    Subclasses should define their own __tablename__ and add type-specific fields.
    """

    __abstract__ = True

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Status tracking
    status: Mapped[TestCaseStatus] = mapped_column(
        String,
        nullable=False,
        default=TestCaseStatus.QUEUED.value,
        index=True,
    )

    # Dataset row reference
    dataset_row_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Total cost for this test case (string to maintain precision)
    total_cost: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )


class DatabaseBaseEvalScore(Base):
    """Base database model for eval scores for experiment results.

    This abstract base class contains common fields shared across all eval score types.
    Subclasses should define their own __tablename__ and add a foreign key to the result model.
    """

    __abstract__ = True

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Eval information
    eval_name: Mapped[str] = mapped_column(String, nullable=False)
    eval_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Eval input variables
    # Structure: [{"variable_name": str, "value": Any}, ...]
    eval_input_variables: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Eval results (broken into separate columns)
    eval_result_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eval_result_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    eval_result_cost: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )
