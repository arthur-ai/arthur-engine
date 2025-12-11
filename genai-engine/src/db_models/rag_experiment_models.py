from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    from db_models.dataset_models import DatabaseDataset


class DatabaseRagExperiment(DatabaseBaseExperiment):
    """Database model for storing RAG experiments associated with tasks"""

    __tablename__ = "rag_experiments"

    # RAG configuration
    # Structure: [SavedRagConfig | UnsavedRagConfig, ...]
    # SavedRagConfig: {"type": "saved", "setting_configuration_id": UUID, "version": int, "query_column": {...}}
    # UnsavedRagConfig: {"type": "unsaved", "unsaved_id": UUID, "rag_provider_id": UUID, "settings": {...}, "query_column": {...}}
    rag_configs: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)

    # Relationships
    test_cases: Mapped[List["DatabaseRagExperimentTestCase"]] = relationship(
        back_populates="experiment",
        lazy="select",
        cascade="all, delete-orphan",
    )

    dataset: Mapped["DatabaseDataset"] = relationship(
        primaryjoin="DatabaseRagExperiment.dataset_id == foreign(DatabaseDataset.id)",
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


class DatabaseRagExperimentTestCase(DatabaseBaseExperimentTestCase):
    """Database model for individual test case results within a RAG experiment"""

    __tablename__ = "rag_experiment_test_cases"

    # Foreign key to experiment
    experiment_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rag_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    experiment: Mapped["DatabaseRagExperiment"] = relationship(
        back_populates="test_cases",
    )
    rag_results: Mapped[List["DatabaseRagExperimentTestCaseRagResult"]] = relationship(
        back_populates="test_case",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabaseRagExperimentTestCaseRagResult(Base):
    """Database model for RAG search execution results within a test case"""

    __tablename__ = "rag_experiment_test_case_rag_results"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign key to test case
    test_case_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rag_experiment_test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # RAG config key for multi-config support: "saved:setting_config_id:version" or "unsaved:uuid"
    rag_config_key: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # RAG config type: "saved" or "unsaved"
    rag_config_type: Mapped[str] = mapped_column(String, nullable=False)

    # RAG configuration information (for saved configs)
    setting_configuration_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID,
        nullable=True,
    )
    setting_configuration_version: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Query text used for the search
    query_text: Mapped[str] = mapped_column(Text, nullable=False)

    # RAG search output stored as JSON
    # Structure: matches RagProviderQueryResponse format
    search_output: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    test_case: Mapped["DatabaseRagExperimentTestCase"] = relationship(
        back_populates="rag_results",
    )
    eval_scores: Mapped[List["DatabaseRagExperimentTestCaseRagResultEvalScore"]] = (
        relationship(
            back_populates="rag_result",
            lazy="select",
            cascade="all, delete-orphan",
        )
    )


class DatabaseRagExperimentTestCaseRagResultEvalScore(DatabaseBaseEvalScore):
    """Database model for eval scores for a RAG result"""

    __tablename__ = "rag_experiment_test_case_rag_result_eval_scores"

    # Foreign key to RAG result
    rag_result_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("rag_experiment_test_case_rag_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    rag_result: Mapped["DatabaseRagExperimentTestCaseRagResult"] = relationship(
        back_populates="eval_scores",
    )
