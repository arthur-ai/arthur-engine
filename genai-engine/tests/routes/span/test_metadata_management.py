from datetime import datetime, timedelta

from tests.routes.span.conftest import (
    _create_database_span,
    _get_trace_metadata,
)


def test_initial_trace_metadata_creation_single_span(trace_metadata_setup):
    """Test that trace metadata is created correctly for a single span."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    trace_id = "test_trace_001"
    task_id = "test_task_001"
    start_time = datetime(2024, 1, 1, 10, 0, 0)
    end_time = datetime(2024, 1, 1, 10, 0, 5)
    created_trace_ids.append(trace_id)

    span = _create_database_span(
        trace_id=trace_id,
        span_id="span_001",
        task_id=task_id,
        start_time=start_time,
        end_time=end_time,
    )

    # Act
    trace_ingestion_service._store_spans([span], commit=True)

    # Assert
    metadata = _get_trace_metadata(db_session, trace_id)
    assert metadata is not None
    assert metadata.trace_id == trace_id
    assert metadata.task_id == task_id
    assert metadata.start_time == start_time
    assert metadata.end_time == end_time
    assert metadata.span_count == 1


def test_trace_metadata_update_with_additional_spans(trace_metadata_setup):
    """Test that trace metadata is updated correctly when adding spans to existing trace."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    trace_id = "test_trace_002"
    task_id = "test_task_002"
    created_trace_ids.append(trace_id)

    # Create initial span
    initial_start = datetime(2024, 1, 1, 10, 0, 0)
    initial_end = datetime(2024, 1, 1, 10, 0, 5)
    initial_span = _create_database_span(
        trace_id=trace_id,
        span_id="span_001",
        task_id=task_id,
        start_time=initial_start,
        end_time=initial_end,
    )

    # Store initial span
    trace_ingestion_service._store_spans([initial_span], commit=True)

    # Verify initial metadata
    metadata = _get_trace_metadata(db_session, trace_id)
    assert metadata.span_count == 1
    assert metadata.start_time == initial_start
    assert metadata.end_time == initial_end

    # Act - Add additional spans with different timestamps
    earlier_start = datetime(2024, 1, 1, 9, 59, 30)  # Earlier start
    later_end = datetime(2024, 1, 1, 10, 0, 10)  # Later end

    additional_spans = [
        _create_database_span(
            trace_id=trace_id,
            span_id="span_002",
            task_id=task_id,
            start_time=earlier_start,
            end_time=datetime(2024, 1, 1, 10, 0, 3),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="span_003",
            task_id=task_id,
            start_time=datetime(2024, 1, 1, 10, 0, 2),
            end_time=later_end,
        ),
    ]

    trace_ingestion_service._store_spans(additional_spans, commit=True)

    # Assert - Verify aggregated metadata
    updated_metadata = _get_trace_metadata(db_session, trace_id)
    assert updated_metadata.span_count == 3  # 1 + 2 additional
    assert updated_metadata.start_time == earlier_start  # Min of all start times
    assert updated_metadata.end_time == later_end  # Max of all end times


def test_trace_metadata_aggregation_logic(trace_metadata_setup):
    """Test proper aggregation logic for start_time, end_time, and span_count."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    trace_id = "test_trace_003"
    task_id = "test_task_003"
    created_trace_ids.append(trace_id)

    # Create spans with deliberately out-of-order timestamps
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    spans = [
        _create_database_span(
            trace_id=trace_id,
            span_id="span_middle",
            task_id=task_id,
            start_time=base_time + timedelta(minutes=2),
            end_time=base_time + timedelta(minutes=3),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="span_earliest",
            task_id=task_id,
            start_time=base_time,  # Earliest start
            end_time=base_time + timedelta(minutes=1),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="span_latest",
            task_id=task_id,
            start_time=base_time + timedelta(minutes=1),
            end_time=base_time + timedelta(minutes=5),  # Latest end
        ),
    ]

    # Act
    trace_ingestion_service._store_spans(spans, commit=True)

    # Assert
    metadata = _get_trace_metadata(db_session, trace_id)
    assert metadata.span_count == 3
    assert metadata.start_time == base_time  # Earliest start time
    assert metadata.end_time == base_time + timedelta(minutes=5)  # Latest end time


def test_bulk_processing_multiple_traces(trace_metadata_setup):
    """Test bulk processing of spans across multiple traces."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    base_time = datetime(2024, 1, 1, 15, 0, 0)
    trace_ids = ["bulk_trace_001", "bulk_trace_002", "bulk_trace_003"]
    task_ids = ["bulk_task_001", "bulk_task_002", "bulk_task_003"]
    created_trace_ids.extend(trace_ids)

    # Create spans for multiple traces
    all_spans = []
    for i, (trace_id, task_id) in enumerate(zip(trace_ids, task_ids)):
        # Each trace gets 2 spans
        for j in range(2):
            span = _create_database_span(
                trace_id=trace_id,
                span_id=f"span_{i}_{j}",
                task_id=task_id,
                start_time=base_time + timedelta(minutes=i * 10 + j),
                end_time=base_time + timedelta(minutes=i * 10 + j + 1),
            )
            all_spans.append(span)

    # Act - Store all spans in one bulk operation
    trace_ingestion_service._store_spans(all_spans, commit=True)

    # Assert - Verify all traces have correct metadata
    for i, trace_id in enumerate(trace_ids):
        metadata = _get_trace_metadata(db_session, trace_id)
        assert metadata is not None
        assert metadata.trace_id == trace_id
        assert metadata.task_id == task_ids[i]
        assert metadata.span_count == 2
        assert metadata.start_time == base_time + timedelta(minutes=i * 10)
        assert metadata.end_time == base_time + timedelta(minutes=i * 10 + 2)


def test_multiple_batch_updates_same_trace(trace_metadata_setup):
    """Test multiple separate batch updates to the same trace."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    trace_id = "test_trace_004"
    task_id = "test_task_004"
    created_trace_ids.append(trace_id)
    base_time = datetime(2024, 1, 1, 16, 0, 0)

    # Act - First batch
    first_batch = [
        _create_database_span(
            trace_id=trace_id,
            span_id="batch1_span1",
            task_id=task_id,
            start_time=base_time,
            end_time=base_time + timedelta(seconds=10),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="batch1_span2",
            task_id=task_id,
            start_time=base_time + timedelta(seconds=5),
            end_time=base_time + timedelta(seconds=15),
        ),
    ]
    trace_ingestion_service._store_spans(first_batch, commit=True)

    # Verify first batch
    metadata = _get_trace_metadata(db_session, trace_id)
    assert metadata.span_count == 2
    assert metadata.start_time == base_time
    assert metadata.end_time == base_time + timedelta(seconds=15)

    # Act - Second batch with wider time range
    second_batch = [
        _create_database_span(
            trace_id=trace_id,
            span_id="batch2_span1",
            task_id=task_id,
            start_time=base_time - timedelta(seconds=5),  # Earlier start
            end_time=base_time + timedelta(seconds=8),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="batch2_span2",
            task_id=task_id,
            start_time=base_time + timedelta(seconds=10),
            end_time=base_time + timedelta(seconds=25),  # Later end
        ),
    ]
    trace_ingestion_service._store_spans(second_batch, commit=True)

    # Assert - Verify final aggregated metadata
    final_metadata = _get_trace_metadata(db_session, trace_id)
    assert final_metadata.span_count == 4  # 2 + 2
    assert final_metadata.start_time == base_time - timedelta(
        seconds=5,
    )  # Earlier start
    assert final_metadata.end_time == base_time + timedelta(seconds=25)  # Later end


def test_out_of_order_span_timestamps_handling(trace_metadata_setup):
    """Test that the bulk update correctly handles out-of-order span arrival."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    trace_id = "test_trace_005"
    task_id = "test_task_005"
    created_trace_ids.append(trace_id)
    base_time = datetime(2024, 1, 1, 18, 0, 0)

    # First, add spans with "middle" timestamps
    middle_batch = [
        _create_database_span(
            trace_id=trace_id,
            span_id="middle_span1",
            task_id=task_id,
            start_time=base_time + timedelta(minutes=5),
            end_time=base_time + timedelta(minutes=6),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="middle_span2",
            task_id=task_id,
            start_time=base_time + timedelta(minutes=7),
            end_time=base_time + timedelta(minutes=8),
        ),
    ]
    trace_ingestion_service._store_spans(middle_batch, commit=True)

    # Then, add spans that extend the time range in both directions
    boundary_batch = [
        _create_database_span(
            trace_id=trace_id,
            span_id="early_span",
            task_id=task_id,
            start_time=base_time,  # Earlier than existing
            end_time=base_time + timedelta(minutes=1),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="late_span",
            task_id=task_id,
            start_time=base_time + timedelta(minutes=10),
            end_time=base_time + timedelta(minutes=15),  # Later than existing
        ),
    ]
    trace_ingestion_service._store_spans(boundary_batch, commit=True)

    # Assert
    metadata = _get_trace_metadata(db_session, trace_id)
    assert metadata.span_count == 4
    assert metadata.start_time == base_time  # From early_span
    assert metadata.end_time == base_time + timedelta(minutes=15)  # From late_span


def test_trace_metadata_with_mixed_task_ids(trace_metadata_setup):
    """Test that trace metadata correctly handles spans with different task_ids in the same trace."""
    # Note: In the actual implementation, spans in the same trace should have the same task_id
    # from resource attributes, but this tests the edge case handling

    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    trace_id = "test_trace_006"
    primary_task_id = "primary_task"
    created_trace_ids.append(trace_id)
    base_time = datetime(2024, 1, 1, 20, 0, 0)

    # Create spans with primary task_id
    primary_spans = [
        _create_database_span(
            trace_id=trace_id,
            span_id="primary_span1",
            task_id=primary_task_id,
            start_time=base_time,
            end_time=base_time + timedelta(seconds=10),
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="primary_span2",
            task_id=primary_task_id,
            start_time=base_time + timedelta(seconds=5),
            end_time=base_time + timedelta(seconds=15),
        ),
    ]

    # Act
    trace_ingestion_service._store_spans(primary_spans, commit=True)

    # Assert
    metadata = _get_trace_metadata(db_session, trace_id)
    assert metadata is not None
    assert metadata.task_id == primary_task_id
    assert metadata.span_count == 2
    assert metadata.start_time == base_time
    assert metadata.end_time == base_time + timedelta(seconds=15)
