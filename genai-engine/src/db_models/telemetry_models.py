from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from arthur_common.models.enums import MetricType
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, IsArchivable

if TYPE_CHECKING:
    from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
    from db_models.task_models import DatabaseTask


class DatabaseTraceMetadata(Base):
    __tablename__ = "trace_metadata"

    trace_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    root_span_resource_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(
            "resource_metadata.id", name="fk_trace_metadata_root_span_resource_id"
        ),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    end_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    span_count: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    total_token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_token_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completion_token_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_token_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    input_content: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    output_content: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    # Relationships
    annotations: Mapped[List["DatabaseAgenticAnnotation"]] = relationship(
        "DatabaseAgenticAnnotation",
        foreign_keys="DatabaseAgenticAnnotation.trace_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_traces_task_start", "task_id", "start_time"),
        Index("idx_traces_task_time_range", "task_id", "start_time", "end_time"),
        Index("idx_traces_user_task_time", "user_id", "task_id", "start_time"),
        Index("idx_traces_user_session", "user_id", "session_id", "start_time"),
        Index(
            "idx_traces_covering",
            "task_id",
            "start_time",
            postgresql_include=[
                "trace_id",
                "end_time",
                "span_count",
                "user_id",
                "session_id",
            ],
        ),
        Index(
            "idx_traces_task_session_time",
            "task_id",
            "session_id",
            "start_time",
            postgresql_where=text("session_id IS NOT NULL"),
        ),
        Index("idx_traces_session_time", "session_id", "start_time"),
        Index("idx_traces_total_token_count", "total_token_count"),
        Index("idx_traces_total_token_cost", "total_token_cost"),
    )


class DatabaseResourceMetadata(Base):
    """Stores OpenTelemetry resource attributes for traces.

    Multiple spans/traces can reference the same resource_id when they
    share identical resource attributes (normalized design).
    """

    __tablename__ = "resource_metadata"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    service_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    resource_attributes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class DatabaseServiceNameTaskMapping(Base):
    """Maps service names to task IDs.

    Immutable once created - mappings are never updated.
    """

    __tablename__ = "service_name_task_mappings"

    service_name: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey(
            "tasks.id", name="fk_service_name_task_mappings_task_id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    task: Mapped["DatabaseTask"] = relationship(
        "DatabaseTask",
        foreign_keys=[task_id],
    )

    __table_args__ = (
        Index("idx_service_name_mapping_task", "service_name", "task_id"),
    )


class DatabaseSpan(Base):
    __tablename__ = "spans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    span_name: Mapped[str | None] = mapped_column(String, nullable=True)
    span_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    end_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("resource_metadata.id", name="fk_spans_resource_id"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("'Unset'"),
    )
    raw_data: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
    )
    prompt_token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    total_token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_token_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completion_token_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_token_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_spans_task_time_kind", "task_id", "start_time", "span_kind"),
        Index(
            "idx_spans_task_span_name",
            "task_id",
            "span_name",
            "start_time",
            postgresql_where=text("span_name IS NOT NULL"),
        ),
        Index("idx_spans_trace_task_time", "trace_id", "task_id", "start_time"),
        Index("idx_spans_user_task_time", "user_id", "task_id", "start_time"),
        Index(
            "idx_spans_llm_task_time",
            "task_id",
            "start_time",
            postgresql_where=text("span_kind = 'LLM'"),
        ),
        Index("idx_spans_total_token_count", "total_token_count"),
        Index("idx_spans_total_token_cost", "total_token_cost"),
    )

    metric_results: Mapped[List["DatabaseMetricResult"]] = relationship(
        "DatabaseMetricResult",
        back_populates="span",
        lazy="joined",
    )


class DatabaseMetric(Base, IsArchivable):
    __tablename__ = "metrics"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    type: Mapped[MetricType] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    metric_metadata: Mapped[str] = mapped_column(String)
    config: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class DatabaseTaskToMetrics(Base):
    __tablename__ = "tasks_to_metrics"
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        index=True,
        primary_key=True,
    )
    metric_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("metrics.id"),
        index=True,
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    task: Mapped["DatabaseTask"] = relationship(back_populates="metric_links")
    metric: Mapped["DatabaseMetric"] = relationship(lazy="joined")


class DatabaseMetricResult(Base):
    __tablename__ = "metric_results"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    metric_type: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
    )  # Native JSON column for MetricScoreDetails
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    span_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("spans.id"),
        nullable=False,
        index=True,
    )
    metric_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("metrics.id"),
        nullable=False,
        index=True,
    )
    span: Mapped["DatabaseSpan"] = relationship(back_populates="metric_results")

    __table_args__ = (
        Index("idx_metric_results_span_id_metric_type", "span_id", "metric_type"),
    )
