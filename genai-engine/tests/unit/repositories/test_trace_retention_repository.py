"""Unit tests for trace retention repository."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db_models import (
    DatabaseResourceMetadata,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTraceMetadata,
)
from repositories.trace_retention_repository import (
    DEFAULT_TRACE_RETENTION_BATCH_SIZE,
    delete_trace_batch,
    get_expired_trace_ids,
)
from tests.clients.base_test_client import override_get_db_session


def _make_task(session: Session) -> str:
    """Create a task and return its id."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    task = DatabaseTask(
        id=task_id,
        name=f"trace_retention_test_{task_id[:8]}",
        created_at=now,
        updated_at=now,
        is_agentic=False,
        archived=False,
    )
    session.add(task)
    session.commit()
    return task_id


@pytest.mark.unit_tests
def test_get_expired_trace_ids_returns_only_expired_and_respects_batch_size() -> None:
    """get_expired_trace_ids returns only trace_ids with end_time < cutoff, capped by batch_size."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)

    # Insert trace_metadata: two expired, one not expired
    expired_1 = str(uuid.uuid4())
    expired_2 = str(uuid.uuid4())
    not_expired = str(uuid.uuid4())
    for trace_id, end_time in [
        (expired_1, now - timedelta(days=2)),
        (expired_2, now - timedelta(days=3)),
        (not_expired, now + timedelta(days=1)),
    ]:
        db_session.add(
            DatabaseTraceMetadata(
                trace_id=trace_id,
                task_id=task_id,
                start_time=end_time - timedelta(seconds=10),
                end_time=end_time,
                span_count=0,
            )
        )
    db_session.commit()

    result = get_expired_trace_ids(db_session, cutoff, batch_size=10)
    assert set(result) == {expired_1, expired_2}
    assert not_expired not in result

    # Respect batch_size; ORDER BY end_time ASC means oldest first
    result_cap = get_expired_trace_ids(db_session, cutoff, batch_size=1)
    assert len(result_cap) == 1
    assert result_cap[0] == expired_2

    # Cleanup
    db_session.execute(
        delete(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.trace_id.in_([expired_1, expired_2, not_expired])
        )
    )
    db_session.execute(delete(DatabaseTask).where(DatabaseTask.id == task_id))
    db_session.commit()
    db_session.close()


@pytest.mark.unit_tests
def test_delete_trace_batch_removes_trace_and_orphan_resource_metadata_only() -> None:
    """delete_trace_batch deletes trace, spans, and only resource_metadata orphaned by this batch."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    trace_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Resource used only by this batch (should be deleted)
    resource_id_batch = str(uuid.uuid4())
    db_session.add(
        DatabaseResourceMetadata(
            id=resource_id_batch,
            service_name="batch-service",
            resource_attributes={},
        )
    )
    # Resource used by another trace (should remain)
    resource_id_other = str(uuid.uuid4())
    db_session.add(
        DatabaseResourceMetadata(
            id=resource_id_other,
            service_name="other-service",
            resource_attributes={},
        )
    )
    db_session.commit()

    # Trace and span for this batch (reference resource_id_batch)
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=trace_id,
            task_id=task_id,
            root_span_resource_id=resource_id_batch,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            span_count=1,
        )
    )
    span_id = str(uuid.uuid4())
    db_session.add(
        DatabaseSpan(
            id=span_id,
            trace_id=trace_id,
            span_id=span_id,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            task_id=task_id,
            resource_id=resource_id_batch,
            raw_data={},
            status_code="Unset",
        )
    )
    # Another trace that references resource_id_other (so it stays)
    other_trace_id = str(uuid.uuid4())
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=other_trace_id,
            task_id=task_id,
            root_span_resource_id=resource_id_other,
            start_time=now,
            end_time=now,
            span_count=0,
        )
    )
    db_session.commit()

    delete_trace_batch(db_session, [trace_id])
    db_session.commit()

    # Batch trace and span gone
    assert (
        db_session.execute(
            select(DatabaseTraceMetadata).where(
                DatabaseTraceMetadata.trace_id == trace_id
            )
        ).scalar_one_or_none()
        is None
    )
    assert (
        db_session.execute(
            select(DatabaseSpan).where(DatabaseSpan.id == span_id)
        ).scalar_one_or_none()
        is None
    )
    # Orphan resource (only referenced by deleted batch) is deleted
    assert (
        db_session.execute(
            select(DatabaseResourceMetadata).where(
                DatabaseResourceMetadata.id == resource_id_batch
            )
        ).scalar_one_or_none()
        is None
    )
    # Resource still referenced by other trace remains
    assert (
        db_session.execute(
            select(DatabaseResourceMetadata).where(
                DatabaseResourceMetadata.id == resource_id_other
            )
        ).scalar_one_or_none()
        is not None
    )
    assert (
        db_session.execute(
            select(DatabaseTraceMetadata).where(
                DatabaseTraceMetadata.trace_id == other_trace_id
            )
        ).scalar_one_or_none()
        is not None
    )

    # Cleanup remaining test data
    db_session.execute(
        delete(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.trace_id == other_trace_id
        )
    )
    db_session.execute(
        delete(DatabaseResourceMetadata).where(
            DatabaseResourceMetadata.id == resource_id_other
        )
    )
    db_session.execute(delete(DatabaseTask).where(DatabaseTask.id == task_id))
    db_session.commit()
    db_session.close()


@pytest.mark.unit_tests
def test_get_expired_trace_ids_empty_cutoff() -> None:
    """get_expired_trace_ids with cutoff in future returns empty list."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)
    trace_id = str(uuid.uuid4())
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=trace_id,
            task_id=task_id,
            start_time=now,
            end_time=now,
            span_count=0,
        )
    )
    db_session.commit()
    cutoff = now + timedelta(days=1)
    result = get_expired_trace_ids(
        db_session, cutoff, batch_size=DEFAULT_TRACE_RETENTION_BATCH_SIZE
    )
    assert result == []
    db_session.execute(
        delete(DatabaseTraceMetadata).where(DatabaseTraceMetadata.trace_id == trace_id)
    )
    db_session.execute(delete(DatabaseTask).where(DatabaseTask.id == task_id))
    db_session.commit()
    db_session.close()
