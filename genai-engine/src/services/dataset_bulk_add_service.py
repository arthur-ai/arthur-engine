"""Service for bulk-adding traces to a dataset.

Given a set of trace IDs, a transform definition, and the dataset's column
schema, this executes the transform against each trace and builds the dataset
rows to persist. This mirrors the single-trace "add to dataset" flow driven by
the frontend (extract via transform, map extracted values onto the dataset's
columns), but for many traces at once.
"""

from uuid import UUID

from arthur_common.models.task_eval_schemas import TraceTransformDefinition

from repositories.span_repository import SpanRepository
from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
)
from schemas.response_schemas import BulkAddTraceResult
from utils.transform_executor import execute_transform


def build_bulk_add_rows(
    span_repo: SpanRepository,
    columns: list[str],
    transform_definition: TraceTransformDefinition,
    trace_ids: list[str],
    org_scope: UUID | None = None,
) -> tuple[list[NewDatasetVersionRowRequest], list[BulkAddTraceResult]]:
    """Execute the transform against each trace and build dataset rows.

    For each trace ID:
      - Fetch the trace (org-scoped). If it does not exist, record a failure.
      - Execute the transform. On unexpected error, record a failure.
      - Otherwise build one row mapping each dataset column to the extracted
        value (missing extractions become an empty string, which is not a
        failure -- matching the single-trace behavior).

    Args:
        span_repo: Repository used to fetch traces by ID.
        columns: Dataset column names that each produced row must fill.
        transform_definition: The transform definition to run against each trace.
        trace_ids: Trace IDs to process, in request order.
        org_scope: Org scope for tenant callers (None for admin callers).

    Returns:
        A tuple of (rows_to_add, per_trace_results). Results are in the same
        order as ``trace_ids``; ``rows_to_add`` contains only the successful
        traces' rows.
    """
    rows: list[NewDatasetVersionRowRequest] = []
    results: list[BulkAddTraceResult] = []

    for trace_id in trace_ids:
        trace = span_repo.get_trace_by_id(
            trace_id=trace_id,
            include_metrics=False,
            compute_new_metrics=False,
            org_scope=org_scope,
        )

        if trace is None:
            results.append(
                BulkAddTraceResult(
                    trace_id=trace_id,
                    success=False,
                    error="trace not found",
                ),
            )
            continue

        try:
            extraction = execute_transform(
                trace=trace,
                transform_definition=transform_definition,
            )
        except Exception as e:
            results.append(
                BulkAddTraceResult(
                    trace_id=trace_id,
                    success=False,
                    error=str(e),
                ),
            )
            continue

        values_by_name = {var.name: var.value for var in extraction.variables}
        row = NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name=column,
                    column_value=values_by_name.get(column, ""),
                )
                for column in columns
            ],
        )
        rows.append(row)
        results.append(BulkAddTraceResult(trace_id=trace_id, success=True))

    return rows, results
