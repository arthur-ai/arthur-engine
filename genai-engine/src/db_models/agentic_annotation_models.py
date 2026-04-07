import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from sqlalchemy import (
    JSON,
    UUID,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TIMESTAMP

from db_models.base import Base

if TYPE_CHECKING:
    from db_models.continuous_eval_test_run_models import DatabaseContinuousEvalTestRun
    from db_models.llm_eval_models import DatabaseContinuousEval


class DatabaseAgenticAnnotation(Base):
    __tablename__ = "agentic_annotations"
    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    annotation_type: Mapped[str] = mapped_column(String, nullable=False)

    # NOTE: trace_id is optional so we can scale horizontally in the future (i.e. adding annotations to spans, etc.)
    trace_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("trace_metadata.trace_id"),
        nullable=True,
        index=True,
    )

    annotation_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    annotation_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Continuous eval run result parameters
    continuous_eval_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("continuous_evals.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    input_variables: Mapped[Optional[List[Dict[str, str]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    run_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    test_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("continuous_eval_test_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Updated at for continuous evals is modified once when the continuous eval was completed
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        nullable=False,
    )

    # Relationships
    continuous_eval: Mapped[Optional["DatabaseContinuousEval"]] = relationship(
        "DatabaseContinuousEval",
        foreign_keys=[continuous_eval_id],
        lazy="selectin",
    )
    test_run: Mapped[Optional["DatabaseContinuousEvalTestRun"]] = relationship(
        "DatabaseContinuousEvalTestRun",
        foreign_keys=[test_run_id],
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "annotation_score IS NULL OR annotation_score IN (0, 1)",
            name="ck_annotation_score_binary",
        ),
        # Required fields for human annotations
        CheckConstraint(
            "(annotation_type != 'human') OR (annotation_score IS NOT NULL)",
            name="ck_human_requires_score",
        ),
        # Required fields for continuous evals
        CheckConstraint(
            "(annotation_type != 'continuous_eval') OR (continuous_eval_id IS NOT NULL)",
            name="ck_continuous_eval_requires_id",
        ),
        CheckConstraint(
            "(annotation_type != 'continuous_eval') OR (run_status IS NOT NULL)",
            name="ck_continuous_eval_requires_run_status",
        ),
        # Composite index for analytics queries
        Index(
            "ix_agentic_annotations_continuous_eval_created",
            "continuous_eval_id",
            "created_at",
        ),
    )
