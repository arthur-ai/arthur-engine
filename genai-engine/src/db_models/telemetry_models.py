from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, IsArchivable


class DatabaseTraceMetadata(Base):
    __tablename__ = "trace_metadata"

    trace_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    end_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    span_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
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
    task_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("tasks.id"),
        nullable=True,
        index=True,
    )
    raw_data: Mapped[dict] = mapped_column(postgresql.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
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
    type: Mapped[str] = mapped_column(String)
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
    details: Mapped[Optional[dict]] = mapped_column(
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
