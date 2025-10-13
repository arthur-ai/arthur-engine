import json
import logging
from datetime import datetime
from typing import Annotated

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import ToolClassEnum
from arthur_common.models.request_schemas import SpanQueryRequest, TraceQueryRequest
from arthur_common.models.response_schemas import (
    QuerySpansResponse,
    QueryTracesWithMetricsResponse,
    SpanWithMetricsResponse,
    TraceResponse,
)
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from google.protobuf.message import DecodeError
from openinference.semconv.trace import OpenInferenceSpanKindValues
from pydantic import ValidationError
from sqlalchemy.orm import Session

from dependencies import get_db_session
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from schemas.response_schemas import (
    SessionListResponse,
    SessionTracesResponse,
    SpanListResponse,
    TraceListResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

logger = logging.getLogger(__name__)

span_routes = APIRouter(
    prefix="/v1",
    route_class=GenaiEngineRoute,
)


def _get_span_repository(db_session: Session) -> SpanRepository:
    """Create and return a SpanRepository instance with required dependencies."""
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    return SpanRepository(db_session, tasks_metrics_repo, metrics_repo)


def _create_response(
    total_spans: int,
    accepted_spans: int,
    rejected_spans: int,
    rejected_reasons: list[str],
) -> Response:
    """Create standardized response for trace processing results."""
    content = {
        "total_spans": total_spans,
        "accepted_spans": accepted_spans,
        "rejected_spans": rejected_spans,
        "rejection_reasons": rejected_reasons,
    }

    if rejected_spans == 0:
        content["status"] = "success"
        status_code = status.HTTP_200_OK
    elif accepted_spans > 0:
        content["status"] = "partial_success"
        status_code = status.HTTP_206_PARTIAL_CONTENT
    else:
        content["status"] = "failure"
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    return Response(
        content=json.dumps(content),
        status_code=status_code,
        media_type="application/json",
    )


def trace_query_parameters(
    # Required parameters
    task_ids: list[str] = Query(
        ...,
        description="Task IDs to filter on. At least one is required.",
        min_length=1,
    ),
    # Optional parameters
    trace_ids: list[str] = Query(
        None,
        description="Trace IDs to filter on. Optional.",
    ),
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format. Use local time (not UTC).",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format. Use local time (not UTC).",
    ),
    tool_name: str = Query(
        None,
        description="Return only results with this tool name.",
    ),
    span_types: list[str] = Query(
        None,
        description=f"Span types to filter on. Optional. Valid values: {', '.join(sorted([kind.value for kind in OpenInferenceSpanKindValues]))}",
    ),
    # Query relevance filters
    query_relevance_eq: float = Query(
        None,
        ge=0,
        le=1,
        description="Equal to this value.",
    ),
    query_relevance_gt: float = Query(
        None,
        ge=0,
        le=1,
        description="Greater than this value.",
    ),
    query_relevance_gte: float = Query(
        None,
        ge=0,
        le=1,
        description="Greater than or equal to this value.",
    ),
    query_relevance_lt: float = Query(
        None,
        ge=0,
        le=1,
        description="Less than this value.",
    ),
    query_relevance_lte: float = Query(
        None,
        ge=0,
        le=1,
        description="Less than or equal to this value.",
    ),
    # Response relevance filters
    response_relevance_eq: float = Query(
        None,
        ge=0,
        le=1,
        description="Equal to this value.",
    ),
    response_relevance_gt: float = Query(
        None,
        ge=0,
        le=1,
        description="Greater than this value.",
    ),
    response_relevance_gte: float = Query(
        None,
        ge=0,
        le=1,
        description="Greater than or equal to this value.",
    ),
    response_relevance_lt: float = Query(
        None,
        ge=0,
        le=1,
        description="Less than this value.",
    ),
    response_relevance_lte: float = Query(
        None,
        ge=0,
        le=1,
        description="Less than or equal to this value.",
    ),
    # Tool classification filters
    tool_selection: ToolClassEnum = Query(
        None,
        description="Tool selection evaluation result.",
    ),
    tool_usage: ToolClassEnum = Query(
        None,
        description="Tool usage evaluation result.",
    ),
    # Trace duration filters
    trace_duration_eq: float = Query(
        None,
        ge=0,
        description="Duration exactly equal to this value (seconds).",
    ),
    trace_duration_gt: float = Query(
        None,
        ge=0,
        description="Duration greater than this value (seconds).",
    ),
    trace_duration_gte: float = Query(
        None,
        ge=0,
        description="Duration greater than or equal to this value (seconds).",
    ),
    trace_duration_lt: float = Query(
        None,
        ge=0,
        description="Duration less than this value (seconds).",
    ),
    trace_duration_lte: float = Query(
        None,
        ge=0,
        description="Duration less than or equal to this value (seconds).",
    ),
) -> TraceQueryRequest:
    """Create a TraceQueryRequest from query parameters."""
    return TraceQueryRequest(
        task_ids=task_ids,
        trace_ids=trace_ids,
        start_time=start_time,
        end_time=end_time,
        tool_name=tool_name,
        span_types=span_types,
        query_relevance_eq=query_relevance_eq,
        query_relevance_gt=query_relevance_gt,
        query_relevance_gte=query_relevance_gte,
        query_relevance_lt=query_relevance_lt,
        query_relevance_lte=query_relevance_lte,
        response_relevance_eq=response_relevance_eq,
        response_relevance_gt=response_relevance_gt,
        response_relevance_gte=response_relevance_gte,
        response_relevance_lt=response_relevance_lt,
        response_relevance_lte=response_relevance_lte,
        tool_selection=tool_selection,
        tool_usage=tool_usage,
        trace_duration_eq=trace_duration_eq,
        trace_duration_gt=trace_duration_gt,
        trace_duration_gte=trace_duration_gte,
        trace_duration_lt=trace_duration_lt,
        trace_duration_lte=trace_duration_lte,
    )


@span_routes.post(
    "/traces",
    summary="Receive Traces",
    description="Receiver for OpenInference trace standard.",
    response_model=None,
    response_model_exclude_none=True,
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def receive_traces(
    body: bytes = Body(...),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Receive and process OpenInference trace data."""
    try:
        span_repo = _get_span_repository(db_session)
        span_results = span_repo.create_traces(body)
        return _create_response(*span_results)
    except DecodeError as e:
        logger.error(f"Failed to decode protobuf message: {e}")
        raise HTTPException(status_code=400, detail="Invalid protobuf message format")
    except Exception as e:
        logger.error(f"Error processing traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/traces/query",
    summary="Query Traces",
    description="Query traces with comprehensive filtering. Returns traces containing spans that match the filters, not just the spans themselves.",
    response_model=QueryTracesWithMetricsResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def query_spans(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    trace_query: Annotated[
        TraceQueryRequest,
        Depends(trace_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Query traces with comprehensive filtering. Returns traces containing spans that match the filters, not just the spans themselves."""
    try:
        span_repo = _get_span_repository(db_session)
        span_count, traces = span_repo.query_traces_with_filters(
            filters=trace_query,
            pagination_parameters=pagination_parameters,
            include_metrics=True,  # Include existing metrics
            compute_new_metrics=False,  # Don't compute new metrics
        )
        return QueryTracesWithMetricsResponse(count=span_count, traces=traces)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying spans: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/traces/metrics/",
    summary="Compute Missing Metrics and Query Traces",
    description="Query traces with comprehensive filtering and compute metrics. Returns traces containing spans that match the filters with computed metrics.",
    response_model=QueryTracesWithMetricsResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def query_spans_with_metrics(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    trace_query: Annotated[
        TraceQueryRequest,
        Depends(trace_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Query traces with comprehensive filtering and compute metrics. Returns traces containing spans that match the filters with computed metrics."""
    try:
        span_repo = _get_span_repository(db_session)
        span_count, traces = span_repo.query_traces_with_filters(
            filters=trace_query,
            pagination_parameters=pagination_parameters,
            include_metrics=True,  # Include existing metrics
            compute_new_metrics=True,  # Compute new metrics
        )
        return QueryTracesWithMetricsResponse(count=span_count, traces=traces)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying spans with metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/spans/query",
    summary="Query Spans By Type",
    description="Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics but does not compute new ones.",
    response_model=QuerySpansResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
    responses={
        400: {"description": "Invalid span types, parameters, or validation error"},
        404: {"description": "No spans found"},
    },
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def query_spans_by_type(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    task_ids: list[str] = Query(
        ...,
        description="Task IDs to filter on. At least one is required.",
        min_length=1,
    ),
    span_types: list[str] = Query(
        None,
        description=f"Span types to filter on. Optional. Valid values: {', '.join(sorted([kind.value for kind in OpenInferenceSpanKindValues]))}",
    ),
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format. Use local time (not UTC).",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format. Use local time (not UTC).",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics but does not compute new ones."""
    try:
        # Validate span_types using our Pydantic model
        query_request = SpanQueryRequest(
            task_ids=task_ids,
            span_types=span_types,
            start_time=start_time,
            end_time=end_time,
        )

        span_repo = _get_span_repository(db_session)
        spans, total_count = span_repo.query_spans(
            task_ids=query_request.task_ids,
            span_types=query_request.span_types,
            start_time=query_request.start_time,
            end_time=query_request.end_time,
            sort=pagination_parameters.sort,
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
            include_metrics=True,  # Include existing metrics
            compute_new_metrics=False,  # Don't compute new metrics
        )
        return QuerySpansResponse(
            count=total_count,
            spans=[span._to_response_model() for span in spans],
        )
    except ValidationError as e:
        # Pydantic validation errors (including our field validators)
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:

        logger.error(f"Value Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying spans: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


# OPTIMIZED TRACE ENDPOINTS


@span_routes.get(
    "/traces",
    summary="List Trace Metadata",
    description="Get lightweight trace metadata for browsing/filtering operations. Returns metadata only without spans or metrics for fast performance.",
    response_model=TraceListResponse,
    response_model_exclude_none=True,
    tags=["Optimized Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_traces_metadata(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    trace_query: Annotated[
        TraceQueryRequest,
        Depends(trace_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get lightweight trace metadata for browsing/filtering operations."""
    try:
        span_repo = _get_span_repository(db_session)
        count, trace_metadata_list = span_repo.get_traces_metadata(
            filters=trace_query,
            pagination_parameters=pagination_parameters,
        )

        traces = [
            trace_metadata._to_metadata_response_model()
            for trace_metadata in trace_metadata_list
        ]
        return TraceListResponse(count=count, traces=traces)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing trace metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/traces/{trace_id}",
    summary="Get Single Trace",
    description="Get complete trace tree with existing metrics (no computation). Returns full trace structure with spans.",
    response_model=TraceResponse,
    response_model_exclude_none=True,
    tags=["Optimized Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_trace_by_id(
    trace_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get complete trace tree with existing metrics (no computation)."""
    try:
        span_repo = _get_span_repository(db_session)
        trace = span_repo.get_trace_by_id(
            trace_id=trace_id,
            include_metrics=True,
            compute_new_metrics=False,
        )

        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        return trace._to_response_model()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace by id: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/traces/{trace_id}/metrics",
    summary="Compute Missing Trace Metrics",
    description="Compute all missing metrics for trace spans on-demand. Returns full trace tree with computed metrics.",
    response_model=TraceResponse,
    response_model_exclude_none=True,
    tags=["Optimized Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def compute_trace_metrics(
    trace_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Compute all missing metrics for trace spans on-demand."""
    try:
        span_repo = _get_span_repository(db_session)
        trace = span_repo.compute_trace_metrics(
            trace_id=trace_id,
        )

        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        return trace._to_response_model()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing trace metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


# OPTIMIZED SPAN ENDPOINTS


@span_routes.get(
    "/spans",
    summary="List Span Metadata",
    description="Get lightweight span metadata for browsing/filtering operations. Returns metadata only without raw data or metrics for fast performance.",
    response_model=SpanListResponse,
    response_model_exclude_none=True,
    tags=["Optimized Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_spans_metadata(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    task_ids: list[str] = Query(
        ...,
        description="Task IDs to filter on. At least one is required.",
        min_length=1,
    ),
    span_types: list[str] = Query(
        None,
        description="Span types to filter on. Optional.",
    ),
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format. Use local time (not UTC).",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format. Use local time (not UTC).",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get lightweight span metadata for browsing/filtering operations."""
    try:
        span_repo = _get_span_repository(db_session)
        # Reuse existing query_spans infrastructure but without metrics
        spans, total_count = span_repo.query_spans(
            task_ids=task_ids,
            span_types=span_types,
            start_time=start_time,
            end_time=end_time,
            sort=pagination_parameters.sort,
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
            include_metrics=False,  # No metrics for metadata endpoint
            compute_new_metrics=False,
        )

        # Transform to metadata response format
        metadata_spans = [span._to_metadata_response_model() for span in spans]
        return SpanListResponse(count=total_count, spans=metadata_spans)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing span metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/spans/{span_id}",
    summary="Get Single Span",
    description="Get single span with existing metrics (no computation). Returns full span object with any existing metrics.",
    response_model=SpanWithMetricsResponse,
    response_model_exclude_none=True,
    tags=["Optimized Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_span_by_id(
    span_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get single span with existing metrics (no computation)."""
    try:
        span_repo = _get_span_repository(db_session)
        span = span_repo.get_span_by_id(
            span_id=span_id,
            include_metrics=True,
            compute_new_metrics=False,
        )

        if not span:
            raise HTTPException(status_code=404, detail=f"Span {span_id} not found")

        return span._to_response_model()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting span by id: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/spans/{span_id}/metrics",
    summary="Compute Missing Span Metrics",
    description="Compute all missing metrics for a single span on-demand. Returns span with computed metrics.",
    response_model=SpanWithMetricsResponse,
    response_model_exclude_none=True,
    tags=["Optimized Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def compute_span_metrics(
    span_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Compute all missing metrics for a single span on-demand."""
    try:
        span_repo = _get_span_repository(db_session)
        span = span_repo.query_span_by_span_id_with_metrics(span_id)

        if not span:
            raise HTTPException(status_code=404, detail=f"Span {span_id} not found")

        return span._to_response_model()
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing span metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


# OPTIMIZED SESSION ENDPOINTS


@span_routes.get(
    "/sessions",
    summary="List Session Metadata",
    description="Get session metadata with pagination and filtering. Returns aggregated session information.",
    response_model=SessionListResponse,
    response_model_exclude_none=True,
    tags=["Optimized Sessions"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_sessions_metadata(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    task_ids: list[str] = Query(
        ...,
        description="Task IDs to filter on. At least one is required.",
        min_length=1,
    ),
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format. Use local time (not UTC).",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format. Use local time (not UTC).",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get session metadata with pagination and filtering."""
    try:
        span_repo = _get_span_repository(db_session)
        count, session_metadata_list = span_repo.get_sessions_metadata(
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            pagination_parameters=pagination_parameters,
        )

        sessions = [
            session_metadata._to_metadata_response_model()
            for session_metadata in session_metadata_list
        ]
        return SessionListResponse(count=count, sessions=sessions)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing session metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/sessions/{session_id}",
    summary="Get Session Traces",
    description="Get all traces in a session. Returns list of full trace trees without metrics computation.",
    response_model=SessionTracesResponse,
    response_model_exclude_none=True,
    tags=["Optimized Sessions"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_session_traces(
    session_id: str,
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get all traces in a session."""
    try:
        span_repo = _get_span_repository(db_session)
        count, traces = span_repo.get_session_traces(
            session_id=session_id,
            pagination_parameters=pagination_parameters,
        )

        if count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or has no traces",
            )

        return SessionTracesResponse(
            session_id=session_id,
            count=count,
            traces=traces,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/sessions/{session_id}/metrics",
    summary="Compute Missing Session Metrics",
    description="Get all traces in a session and compute missing metrics. Returns list of full trace trees with computed metrics.",
    response_model=SessionTracesResponse,
    response_model_exclude_none=True,
    tags=["Optimized Sessions"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def compute_session_metrics(
    session_id: str,
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get all traces in a session and compute missing metrics."""
    try:
        span_repo = _get_span_repository(db_session)
        count, traces = span_repo.compute_session_metrics(
            session_id=session_id,
            pagination_parameters=pagination_parameters,
        )

        if count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or has no traces",
            )

        return SessionTracesResponse(
            session_id=session_id,
            count=count,
            traces=traces,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing session metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
