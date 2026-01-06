from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, ForeignKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from db_models.base import Base
from db_models.base_experiment_models import (
    DatabaseBaseEvalScore,
    DatabaseBaseExperiment,
    DatabaseBaseExperimentTestCase,
)

# TYPE_CHECKING is False at runtime but True during static type checking.
# This avoids circular import errors (notebook_models imports this file)
# while still providing type hints for IDEs and mypy.
if TYPE_CHECKING:
    from db_models.agentic_notebook_models import DatabaseAgenticNotebook
    from db_models.dataset_models import DatabaseDataset


class DatabaseAgenticExperiment(DatabaseBaseExperiment):
    """Database model for storing agentic experiments associated with tasks"""

    __tablename__ = "agentic_experiments"

    # Foreign key to agentic notebook (optional)
    notebook_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("agentic_notebooks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # HTTP template configuration stored as JSON
    # Structure: {"endpoint_name": str, "endpoint_url": str, "headers": [...], "request_body": {...}}
    http_template: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Template variable mappings stored as JSON
    # Structure: [{"variable_name": str, "source": {...}}, ...]
    # NOTE: Request-time parameters are automatically filtered out by the validator
    template_variable_mapping: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )

    @validates("template_variable_mapping")
    def _filter_request_time_parameters(
        self,
        key: str,
        value: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Automatically filter out request-time parameters before saving to database.

        Request-time parameters should never be saved to the database as they are
        provided at execution time. This validator ensures they are removed
        whenever template_variable_mapping is set.
        """
        if not value:
            return value

        filtered = []
        for mapping in value:
            # Only save mappings that are NOT request-time parameters
            source = mapping.get("source", {})
            if source.get("type") != "request_time_parameter":
                filtered.append(mapping)
        return filtered

    # Relationships
    notebook: Mapped[Optional["DatabaseAgenticNotebook"]] = relationship(
        back_populates="experiments",
    )
    test_cases: Mapped[List["DatabaseAgenticExperimentTestCase"]] = relationship(
        back_populates="experiment",
        lazy="select",
        cascade="all, delete-orphan",
    )

    dataset: Mapped["DatabaseDataset"] = relationship(
        primaryjoin="DatabaseAgenticExperiment.dataset_id == foreign(DatabaseDataset.id)",
        lazy="select",
        viewonly=True,
    )

    # Table args for composite foreign key (inherited from BaseExperiment, but explicitly defined here)
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "dataset_version"],
            ["dataset_versions.dataset_id", "dataset_versions.version_number"],
        ),
    )


class DatabaseAgenticExperimentTestCase(DatabaseBaseExperimentTestCase):
    """Database model for individual test case results within an agentic experiment"""

    __tablename__ = "agentic_experiment_test_cases"

    # Foreign key to experiment
    experiment_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agentic_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Template input variables for this test case (with values resolved)
    # Structure: [{"variable_name": str, "value": str}, ...]
    # NOTE: Request-time parameters should not be included
    template_input_variables: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Relationships
    experiment: Mapped["DatabaseAgenticExperiment"] = relationship(
        back_populates="test_cases",
    )
    agentic_result: Mapped[
        Optional["DatabaseAgenticExperimentTestCaseAgenticResult"]
    ] = relationship(
        back_populates="test_case",
        lazy="select",
        cascade="all, delete-orphan",
        uselist=False,
    )


class DatabaseAgenticExperimentTestCaseAgenticResult(Base):
    """Database model for agent HTTP request execution results within a test case"""

    __tablename__ = "agentic_experiment_test_case_agentic_results"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign key to test case (one-to-one relationship)
    test_case_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agentic_experiment_test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )

    # Request details (with variables resolved)
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    request_headers: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False)
    request_body: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Response details stored as JSON
    # Structure: {"response_body": {...}, "status_code": int | None, "trace_id": str | None}
    response_output: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    test_case: Mapped["DatabaseAgenticExperimentTestCase"] = relationship(
        back_populates="agentic_result",
    )
    eval_scores: Mapped[
        List["DatabaseAgenticExperimentTestCaseAgenticResultEvalScore"]
    ] = relationship(
        back_populates="agentic_result",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabaseAgenticExperimentTestCaseAgenticResultEvalScore(DatabaseBaseEvalScore):
    """Database model for eval scores for an agentic result"""

    __tablename__ = "agentic_experiment_test_case_agentic_result_eval_scores"

    # Foreign key to agentic result
    agentic_result_id: Mapped[str] = mapped_column(
        String,
        ForeignKey(
            "agentic_experiment_test_case_agentic_results.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # Relationships
    agentic_result: Mapped["DatabaseAgenticExperimentTestCaseAgenticResult"] = (
        relationship(back_populates="eval_scores")
    )
