"""Repository for trace data retention: delete traces older than a cutoff in batches."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db_models import (
    DatabaseAgenticAnnotation,
    DatabaseMetricResult,
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
    """Return up to batch_size trace_ids from trace_metadata with end_time < cutoff.

    Uses ``FOR UPDATE SKIP LOCKED`` so concurrent callers don't block each other.
    Under contention this may return fewer than *batch_size* rows (even zero) when
    eligible rows exist but are locked by another session.  Callers in a
    multi-instance deployment should not treat an empty result as "all done."
    """
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
    Order: agentic_annotations -> metric_results -> spans -> trace_metadata.

    Resource metadata is intentionally preserved — resources are logical
    groupings of traces and should outlive individual trace retention.
    """
    if not trace_ids:
        return

    # 1. Agentic annotations for these traces
    db_session.execute(
        delete(DatabaseAgenticAnnotation).where(
            DatabaseAgenticAnnotation.trace_id.in_(trace_ids)
        )
    )

    # 2. Lock span rows (prevents concurrent metric_result inserts via FK check
    # blocking) and collect span_ids.
    span_rows_stmt = (
        select(DatabaseSpan.id)
        .where(DatabaseSpan.trace_id.in_(trace_ids))
        .with_for_update()
    )
    span_ids = [row[0] for row in db_session.execute(span_rows_stmt).all()]

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

    logger.info(
        "Trace retention: deleted batch of %d traces (%d spans)",
        len(trace_ids),
        len(span_ids),
    )
