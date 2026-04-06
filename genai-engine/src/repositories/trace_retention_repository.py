"""Repository for trace data retention: delete traces older than a cutoff in batches."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db_models import (
    DatabaseAgenticAnnotation,
    DatabaseMetricResult,
    DatabaseResourceMetadata,
    DatabaseSpan,
    DatabaseTraceMetadata,
)

logger = logging.getLogger(__name__)

DEFAULT_TRACE_RETENTION_BATCH_SIZE = 500


def get_expired_trace_ids(
    db_session: Session,
    cutoff: datetime,
    batch_size: int = DEFAULT_TRACE_RETENTION_BATCH_SIZE,
) -> list[str]:
    """Return up to batch_size trace_ids from trace_metadata with end_time < cutoff."""
    stmt = (
        select(DatabaseTraceMetadata.trace_id)
        .where(DatabaseTraceMetadata.end_time < cutoff)
        .order_by(DatabaseTraceMetadata.end_time.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    rows = db_session.execute(stmt).all()
    return [row[0] for row in rows]


def delete_trace_batch(db_session: Session, trace_ids: list[str]) -> None:
    """
    Delete one batch of traces and related rows in FK-safe order.
    Order: agentic_annotations -> metric_results -> spans -> trace_metadata -> orphan resource_metadata.
    """
    if not trace_ids:
        return

    # 1. Agentic annotations for these traces
    db_session.execute(
        delete(DatabaseAgenticAnnotation).where(
            DatabaseAgenticAnnotation.trace_id.in_(trace_ids)
        )
    )

    # 2. Span ids for these traces (for metric_results)
    span_ids_stmt = select(DatabaseSpan.id).where(DatabaseSpan.trace_id.in_(trace_ids))
    span_ids = [row[0] for row in db_session.execute(span_ids_stmt).all()]

    # Collect resource_ids referenced by this batch (before we delete spans/trace_metadata)
    # so we only delete orphan resource_metadata that belonged to this batch.
    batch_resource_ids_stmt = (
        select(DatabaseSpan.resource_id)
        .where(
            DatabaseSpan.trace_id.in_(trace_ids),
            DatabaseSpan.resource_id.isnot(None),
        )
        .distinct()
    )
    batch_resource_ids = [
        row[0] for row in db_session.execute(batch_resource_ids_stmt).all()
    ]
    trace_resource_ids_stmt = (
        select(DatabaseTraceMetadata.root_span_resource_id)
        .where(
            DatabaseTraceMetadata.trace_id.in_(trace_ids),
            DatabaseTraceMetadata.root_span_resource_id.isnot(None),
        )
        .distinct()
    )
    batch_resource_ids.extend(
        row[0] for row in db_session.execute(trace_resource_ids_stmt).all()
    )
    batch_resource_ids = list(
        dict.fromkeys(batch_resource_ids)
    )  # unique, preserve order

    if span_ids:
        db_session.execute(
            delete(DatabaseMetricResult).where(
                DatabaseMetricResult.span_id.in_(span_ids)
            )
        )

    # 3. Spans for these traces
    db_session.execute(delete(DatabaseSpan).where(DatabaseSpan.trace_id.in_(trace_ids)))

    # 4. Trace metadata
    db_session.execute(
        delete(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.trace_id.in_(trace_ids)
        )
    )

    # 5. Orphan resource_metadata: only those referenced by this batch and no longer referenced elsewhere
    if batch_resource_ids:
        remaining_span_resource_ids = (
            select(DatabaseSpan.resource_id)
            .where(DatabaseSpan.resource_id.in_(batch_resource_ids))
            .distinct()
        )
        remaining_trace_resource_ids = (
            select(DatabaseTraceMetadata.root_span_resource_id)
            .where(DatabaseTraceMetadata.root_span_resource_id.in_(batch_resource_ids))
            .distinct()
        )
        db_session.execute(
            delete(DatabaseResourceMetadata).where(
                DatabaseResourceMetadata.id.in_(batch_resource_ids),
                ~DatabaseResourceMetadata.id.in_(remaining_span_resource_ids),
                ~DatabaseResourceMetadata.id.in_(remaining_trace_resource_ids),
            )
        )

    logger.info(
        "Trace retention: deleted batch of %d traces (%d spans)",
        len(trace_ids),
        len(span_ids),
    )
