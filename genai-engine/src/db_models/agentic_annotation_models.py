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
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TIMESTAMP

from db_models.base import Base

if TYPE_CHECKING:
    from db_models.llm_eval_models import DatabaseContinuousEval

_LIVE_SPAN_RUNS = "run_level = 'span' AND test_run_id IS NULL"
_TEST_SPAN_RUNS = "run_level = 'span' AND test_run_id IS NOT NULL"


class DatabaseAgenticAnnotation(Base):
    __tablename__ = "agentic_annotations"
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
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
    # Span the annotation is about; NULL for the whole trace.
    span_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Category of the result (e.g. "wrong_tool"), from a person or a judge.
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # ContinuousEvalRunLevel: 'trace' (every human annotation and every trace-scope
    # run), 'span' (one judged span of a span-scope eval) or 'span_rollup' (the
    # trace's summary of its span runs). Trace-level reads leave 'span' rows out.
    run_level: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="trace",
        server_default="trace",
    )
    # Spans in the trace when the run judged it. A run is stale when the trace now
    # has more spans (late spans); nothing re-runs it automatically yet.
    judged_span_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
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

    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
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
        # The daily spend cap sums each eval's runs judged since midnight.
        Index(
            "ix_agentic_annotations_continuous_eval_updated",
            "continuous_eval_id",
            "updated_at",
        ),
        # A retried fan-out never makes a second span run for the same span, live
        # or within one test run.
        Index(
            "uq_agentic_annotations_live_span_run",
            "continuous_eval_id",
            "trace_id",
            "span_id",
            unique=True,
            postgresql_where=text(_LIVE_SPAN_RUNS),
            sqlite_where=text(_LIVE_SPAN_RUNS),
        ),
        Index(
            "uq_agentic_annotations_test_span_run",
            "continuous_eval_id",
            "trace_id",
            "span_id",
            "test_run_id",
            unique=True,
            postgresql_where=text(_TEST_SPAN_RUNS),
            sqlite_where=text(_TEST_SPAN_RUNS),
        ),
    )
