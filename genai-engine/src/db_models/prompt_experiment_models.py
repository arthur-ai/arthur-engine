from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from litellm import ChatCompletionMessageToolCall
from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
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
    from db_models.notebook_models import DatabaseNotebook


class DatabasePromptExperiment(DatabaseBaseExperiment):
    """Database model for storing prompt experiments associated with tasks"""

    __tablename__ = "prompt_experiments"

    # Multi-prompt configuration
    # Structure: [SavedPromptConfig | UnsavedPromptConfig, ...]
    # SavedPromptConfig: {"type": "saved", "name": str, "version": int}
    # UnsavedPromptConfig: {"type": "unsaved", "auto_name": str, "messages": [...], "model_name": str, "model_provider": str, "tools": [...], "config": {...}, "variables": [...]}
    prompt_configs: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)

    # Variable mappings stored as JSON
    # Structure: [{"variable_name": str, "source": {"type": str, "dataset_column": {...}, ...}}]
    prompt_variable_mapping: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Relationships
    notebook: Mapped[Optional["DatabaseNotebook"]] = relationship(
        back_populates="experiments",
    )
    test_cases: Mapped[List["DatabasePromptExperimentTestCase"]] = relationship(
        back_populates="experiment",
        lazy="select",
        cascade="all, delete-orphan",
    )

    dataset: Mapped["DatabaseDataset"] = relationship(
        primaryjoin="DatabasePromptExperiment.dataset_id == foreign(DatabaseDataset.id)",
        lazy="select",
        viewonly=True,
    )


class DatabasePromptExperimentTestCase(DatabaseBaseExperimentTestCase):
    """Database model for individual test case results within a prompt experiment"""

    __tablename__ = "prompt_experiment_test_cases"

    # Foreign key to experiment
    experiment_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("prompt_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Input variables for this test case
    # Structure: [{"variable_name": str, "value": str}, ...]
    prompt_input_variables: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Relationships
    experiment: Mapped["DatabasePromptExperiment"] = relationship(
        back_populates="test_cases",
    )
    prompt_results: Mapped[List["DatabasePromptExperimentTestCasePromptResult"]] = (
        relationship(
            back_populates="test_case",
            lazy="select",
            cascade="all, delete-orphan",
        )
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

    # Prompt key for multi-prompt support: "saved:name:version" or "unsaved:auto_name"
    prompt_key: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Prompt type: "saved" or "unsaved"
    prompt_type: Mapped[str] = mapped_column(String, nullable=False)

    # Prompt information (for saved prompts)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Unsaved prompt auto-name (for unsaved prompts)
    unsaved_prompt_auto_name: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    # Rendered prompt with variables replaced
    rendered_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # Output from the prompt (broken into separate columns)
    output_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_tool_calls: Mapped[Optional[List[ChatCompletionMessageToolCall]]] = (
        mapped_column(JSON, nullable=True)
    )
    output_cost: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    test_case: Mapped["DatabasePromptExperimentTestCase"] = relationship(
        back_populates="prompt_results",
    )
    eval_scores: Mapped[
        List["DatabasePromptExperimentTestCasePromptResultEvalScore"]
    ] = relationship(
        back_populates="prompt_result",
        lazy="select",
        cascade="all, delete-orphan",
    )


class DatabasePromptExperimentTestCasePromptResultEvalScore(DatabaseBaseEvalScore):
    """Database model for eval scores for a prompt result"""

    __tablename__ = "prompt_experiment_test_case_prompt_result_eval_scores"

    # Foreign key to prompt result
    prompt_result_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("prompt_experiment_test_case_prompt_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    prompt_result: Mapped["DatabasePromptExperimentTestCasePromptResult"] = (
        relationship(back_populates="eval_scores")
    )
