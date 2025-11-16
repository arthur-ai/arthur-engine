from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base
from schemas.prompt_experiment_schemas import ExperimentStatus, TestCaseStatus


class DatabasePromptExperiment(Base):
    """Database model for storing prompt experiments associated with tasks"""

    __tablename__ = "prompt_experiments"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign key to task
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
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

    # Prompt being tested
    prompt_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    prompt_versions: Mapped[List[int]] = mapped_column(
        JSON, nullable=False
    )  # List of versions to test

    # Dataset reference
    dataset_id: Mapped[str] = mapped_column(String, nullable=False)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Variable mappings stored as JSON
    # Structure: [{"variable_name": str, "source": {"type": str, "dataset_column": {...}, ...}}]
    prompt_variable_mapping: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )

    # Eval configurations stored as JSON
    # Structure: [{"name": str, "version": str, "variable_mapping": [...]}, ...]
    eval_configs: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)

    # Summary statistics (denormalized for quick access)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Summary results stored as JSON (computed after experiment completes)
    # Structure: {"prompt_eval_summaries": [{"prompt_name": str, "prompt_version": str, "eval_results": [...]}]}
    summary_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    # Relationships
    test_cases: Mapped[List["DatabasePromptExperimentTestCase"]] = relationship(
        back_populates="experiment",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabasePromptExperimentTestCase(Base):
    """Database model for individual test case results within a prompt experiment"""

    __tablename__ = "prompt_experiment_test_cases"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign key to experiment
    experiment_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("prompt_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status tracking
    status: Mapped[TestCaseStatus] = mapped_column(
        String,
        nullable=False,
        default=TestCaseStatus.QUEUED.value,
        index=True,
    )

    # Dataset row reference
    dataset_row_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Input variables for this test case
    # Structure: [{"variable_name": str, "value": str}, ...]
    prompt_input_variables: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )

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

    # Relationships
    experiment: Mapped["DatabasePromptExperiment"] = relationship(
        back_populates="test_cases"
    )
    prompt_results: Mapped[List["DatabasePromptExperimentTestCasePromptResult"]] = relationship(
        back_populates="test_case",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabasePromptExperimentTestCasePromptResult(Base):
    """Database model for prompt execution results within a test case"""

    __tablename__ = "prompt_experiment_test_case_prompt_results"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign key to test case
    test_case_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("prompt_experiment_test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Prompt information
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Rendered prompt with variables replaced
    rendered_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # Output from the prompt
    # Structure: {"content": str, "tool_calls": [], "cost": str}
    output: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    test_case: Mapped["DatabasePromptExperimentTestCase"] = relationship(
        back_populates="prompt_results"
    )
    eval_scores: Mapped[List["DatabasePromptExperimentTestCasePromptResultEvalScore"]] = relationship(
        back_populates="prompt_result",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabasePromptExperimentTestCasePromptResultEvalScore(Base):
    """Database model for eval scores for a prompt result"""

    __tablename__ = "prompt_experiment_test_case_prompt_result_eval_scores"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign key to prompt result
    prompt_result_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("prompt_experiment_test_case_prompt_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Eval information
    eval_name: Mapped[str] = mapped_column(String, nullable=False)
    eval_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Eval input variables
    # Structure: [{"variable_name": str, "value": Any}, ...]
    eval_input_variables: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )

    # Eval results
    # Structure: {"score": float, "explanation": str, "cost": float}
    eval_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    prompt_result: Mapped["DatabasePromptExperimentTestCasePromptResult"] = relationship(
        back_populates="eval_scores"
    )
