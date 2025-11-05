from datetime import datetime, timedelta

from tests.routes.legacy_span.conftest import (
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
    assert metadata.session_id is None  # No session_id provided
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
    assert metadata.session_id is None  # No session_id provided
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
    assert metadata.session_id is None  # No session_id provided
    assert metadata.span_count == 2
    assert metadata.start_time == base_time
    assert metadata.end_time == base_time + timedelta(seconds=15)


def test_trace_metadata_session_id_storage_and_conflict_resolution(
    trace_metadata_setup,
):
    """Test session_id storage and conflict resolution when multiple spans have different session_ids."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup
    trace_id = "test_trace_session_001"
    task_id = "test_task_session_001"
    created_trace_ids.append(trace_id)

    base_time = datetime(2024, 1, 1, 12, 0, 0)
    first_session_id = "session_first_12345"
    second_session_id = "session_second_67890"

    # Test 1: Single span with session_id should be stored
    single_span = _create_database_span(
        trace_id=trace_id,
        span_id="span_single",
        task_id=task_id,
        start_time=base_time,
        end_time=base_time + timedelta(seconds=1),
        session_id=first_session_id,
    )
    trace_ingestion_service._store_spans([single_span], commit=True)

    metadata = _get_trace_metadata(db_session, trace_id)
    assert metadata.session_id == first_session_id
    assert metadata.span_count == 1

    # Test 2: Add spans with conflicting session_ids - should use first non-null
    conflicting_spans = [
        _create_database_span(
            trace_id=trace_id,
            span_id="span_002",
            task_id=task_id,
            start_time=base_time + timedelta(seconds=2),
            end_time=base_time + timedelta(seconds=7),
            session_id=second_session_id,  # Different session_id
        ),
        _create_database_span(
            trace_id=trace_id,
            span_id="span_003",
            task_id=task_id,
            start_time=base_time + timedelta(seconds=4),
            end_time=base_time + timedelta(seconds=9),
            session_id=None,  # No session_id
        ),
    ]

    # Act
    trace_ingestion_service._store_spans(conflicting_spans, commit=True)

    # Assert - Should preserve existing session_id (first_session_id)
    final_metadata = _get_trace_metadata(db_session, trace_id)
    assert final_metadata.session_id == first_session_id  # Should preserve existing
    assert final_metadata.span_count == 3


def test_trace_metadata_session_id_update_logic(trace_metadata_setup):
    """Test session_id update logic: preservation of existing values and updating null values."""
    # Arrange
    db_session, trace_ingestion_service, created_trace_ids = trace_metadata_setup

    # Test Case 1: Null session_id gets updated when new spans have session_id
    trace_id_1 = "test_trace_session_null_update"
    task_id_1 = "test_task_session_null_update"
    created_trace_ids.extend([trace_id_1])
    base_time_1 = datetime(2024, 1, 1, 14, 0, 0)
    new_session_id = "new_session_12345"

    # Create metadata with null session_id
    null_batch = [
        _create_database_span(
            trace_id=trace_id_1,
            span_id="null_span1",
            task_id=task_id_1,
            start_time=base_time_1,
            end_time=base_time_1 + timedelta(seconds=5),
            session_id=None,  # No session_id
        ),
    ]
    trace_ingestion_service._store_spans(null_batch, commit=True)

    metadata = _get_trace_metadata(db_session, trace_id_1)
    assert metadata.session_id is None
    assert metadata.span_count == 1

    # Add spans with session_id - should update null to new session_id
    update_batch = [
        _create_database_span(
            trace_id=trace_id_1,
            span_id="update_span1",
            task_id=task_id_1,
            start_time=base_time_1 + timedelta(seconds=10),
            end_time=base_time_1 + timedelta(seconds=15),
            session_id=new_session_id,
        ),
    ]
    trace_ingestion_service._store_spans(update_batch, commit=True)

    final_metadata_1 = _get_trace_metadata(db_session, trace_id_1)
    assert (
        final_metadata_1.session_id == new_session_id
    )  # Should update null to new session_id
    assert final_metadata_1.span_count == 2

    # Test Case 2: Existing session_id is preserved during updates
    trace_id_2 = "test_trace_session_preserve"
    task_id_2 = "test_task_session_preserve"
    created_trace_ids.extend([trace_id_2])
    base_time_2 = datetime(2024, 1, 1, 16, 0, 0)
    existing_session_id = "existing_session_67890"
    different_session_id = "different_session_99999"

    # Establish metadata with existing session_id
    existing_batch = [
        _create_database_span(
            trace_id=trace_id_2,
            span_id="existing_span1",
            task_id=task_id_2,
            start_time=base_time_2,
            end_time=base_time_2 + timedelta(seconds=5),
            session_id=existing_session_id,
        ),
    ]
    trace_ingestion_service._store_spans(existing_batch, commit=True)

    metadata = _get_trace_metadata(db_session, trace_id_2)
    assert metadata.session_id == existing_session_id
    assert metadata.span_count == 1

    # Add spans with different session_id - should preserve existing
    preserve_batch = [
        _create_database_span(
            trace_id=trace_id_2,
            span_id="preserve_span1",
            task_id=task_id_2,
            start_time=base_time_2 + timedelta(seconds=10),
            end_time=base_time_2 + timedelta(seconds=15),
            session_id=different_session_id,  # Different session_id
        ),
    ]
    trace_ingestion_service._store_spans(preserve_batch, commit=True)

    final_metadata_2 = _get_trace_metadata(db_session, trace_id_2)
    assert (
        final_metadata_2.session_id == existing_session_id
    )  # Should preserve existing
    assert final_metadata_2.span_count == 2
