import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.response_schemas import (
    AgenticAnnotationResponse,
    ListAgenticAnnotationsResponse,
    SpanWithMetricsResponse,
    TraceResponse,
)
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from google.protobuf.message import DecodeError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from dependencies import get_db_session
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v1.legacy_span_routes import (
    ExtendedTraceQuery,
    _create_response,
    trace_query_parameters,
)
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from schemas.request_schemas import (
    AgenticAnnotationListFilterRequest,
    AgenticAnnotationRequest,
)
from schemas.response_schemas import (
    SessionListResponse,
    SessionTracesResponse,
    SpanListResponse,
    TraceListResponse,
    TraceUserListResponse,
    TraceUserMetadataResponse,
    UnregisteredRootSpanGroup,
    UnregisteredRootSpansResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

logger = logging.getLogger(__name__)

trace_api_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


def _get_span_repository(db_session: Session) -> SpanRepository:
    """Create and return a SpanRepository instance with required dependencies."""
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    return SpanRepository(db_session, tasks_metrics_repo, metrics_repo)


# TRACE ENDPOINTS


@trace_api_routes.post(
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
) -> Response:
    """Receive and process OpenInference trace data."""
    try:
        span_repo = _get_span_repository(db_session)
        db_spans, span_results = span_repo.create_traces(body)

        # Enqueue continuous evals for root spans
        continuous_evals_repo = ContinuousEvalsRepository(db_session)
        continuous_evals_repo.enqueue_continuous_evals_for_root_spans(db_spans)

        return _create_response(*span_results)
    except DecodeError as e:
        logger.error(f"Failed to decode protobuf message: {e}")
        raise HTTPException(status_code=400, detail="Invalid protobuf message format")
    except Exception as e:
        logger.error(f"Error processing traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@trace_api_routes.get(
    "/traces",
    summary="List Trace Metadata",
    description="Get lightweight trace metadata for browsing/filtering operations. Returns metadata only without spans or metrics for fast performance. Set include_spans=true to include flat list of spans for each trace.",
    response_model=TraceListResponse,
    response_model_exclude_none=True,
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_traces_metadata(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    extended_query: Annotated[
        ExtendedTraceQuery,
        Depends(trace_query_parameters),
    ],
    include_spans: bool = Query(
        False,
        description="Include flat list of spans for each trace. Defaults to false for performance.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TraceListResponse:
    """Get lightweight trace metadata for browsing/filtering operations."""
    try:
        span_repo = _get_span_repository(db_session)
        count, trace_metadata_list = span_repo.get_traces_metadata(
            filters=extended_query.trace_query,
            pagination_parameters=pagination_parameters,
            user_ids=extended_query.trace_query.user_ids,
            include_spans=include_spans,
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


# SPAN ENDPOINTS


@trace_api_routes.get(
    "/traces/spans",
    summary="List Span Metadata with Filtering",
    description="Get lightweight span metadata with comprehensive filtering support. Returns individual spans that match filtering criteria with the same filtering capabilities as trace filtering. Supports trace-level filters, span-level filters, and metric filters.",
    response_model=SpanListResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_spans_metadata(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    extended_query: Annotated[
        ExtendedTraceQuery,
        Depends(trace_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> SpanListResponse:
    """Get lightweight span metadata for browsing/filtering operations."""
    try:
        span_repo = _get_span_repository(db_session)

        # Use query_spans with comprehensive filtering via filters parameter
        spans, total_count = span_repo.query_spans(
            sort=pagination_parameters.sort,
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
            include_metrics=False,  # No metrics for metadata endpoint
            compute_new_metrics=False,
            filters=extended_query.trace_query,  # Enables comprehensive filtering
            span_duration_filters=extended_query.span_duration_filters,  # Span duration filtering
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


# ============================================================================
# UNREGISTERED TRACES ENDPOINTS
# ============================================================================


@trace_api_routes.get(
    "/traces/spans/unregistered",
    summary="Get Unregistered Root Spans",
    description="Get grouped root spans for traces without task_id. Groups are ordered by count descending. Supports pagination. Time bounds (start_time/end_time) are recommended for performance on large datasets.",
    response_model=UnregisteredRootSpansResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_unregistered_root_spans(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format. Use local time (not UTC).",
    ),
    end_time: datetime = Query(
        None,
        description="Inclusive end date in ISO8601 string format. Use local time (not UTC).",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> UnregisteredRootSpansResponse:
    """Get grouped root spans for traces without task_id with pagination."""
    try:
        span_repo = _get_span_repository(db_session)
        groups_dict, total_count = span_repo.get_unregistered_root_spans_grouped(
            pagination_parameters=pagination_parameters,
            start_time=start_time,
            end_time=end_time,
        )

        # Convert dicts to UnregisteredRootSpanGroup objects
        groups = [
            UnregisteredRootSpanGroup(
                span_name=group["span_name"],
                count=group["count"],
            )
            for group in groups_dict
        ]

        return UnregisteredRootSpansResponse(
            groups=groups,
            total_count=total_count,
        )
    except Exception as e:
        logger.error(f"Error getting unregistered root spans: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@trace_api_routes.get(
    "/traces/spans/{span_id}",
    summary="Get Single Span",
    description="Get single span with existing metrics (no computation). Returns full span object with any existing metrics.",
    response_model=SpanWithMetricsResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_span_by_id(
    span_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> SpanWithMetricsResponse:
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


@trace_api_routes.get(
    "/traces/spans/{span_id}/metrics",
    summary="Compute Missing Span Metrics",
    description="Compute all missing metrics for a single span on-demand. Returns span with computed metrics.",
    response_model=SpanWithMetricsResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def compute_span_metrics(
    span_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> SpanWithMetricsResponse:
    """Compute all missing metrics for a single span on-demand."""
    try:
        span_repo = _get_span_repository(db_session)
        span = span_repo.compute_span_metrics(span_id)

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


# SESSION ENDPOINTS


@trace_api_routes.get(
    "/traces/sessions",
    summary="List Session Metadata",
    description="Get session metadata with pagination and filtering. Returns aggregated session information.",
    response_model=SessionListResponse,
    response_model_exclude_none=True,
    tags=["Sessions"],
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
    user_ids: list[str] = Query(
        None,
        description="User IDs to filter on. Optional.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> SessionListResponse:
    """Get session metadata with pagination and filtering."""
    try:
        span_repo = _get_span_repository(db_session)
        count, session_metadata_list = span_repo.get_sessions_metadata(
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            user_ids=user_ids,
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


@trace_api_routes.get(
    "/traces/sessions/{session_id}",
    summary="Get Session Traces",
    description="Get all traces in a session. Returns list of full trace trees with existing metrics (no computation).",
    response_model=SessionTracesResponse,
    response_model_exclude_none=True,
    tags=["Sessions"],
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
) -> SessionTracesResponse:
    """Get all traces in a session with existing metrics (no computation)."""
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


@trace_api_routes.get(
    "/traces/sessions/{session_id}/metrics",
    summary="Compute Missing Session Metrics",
    description="Get all traces in a session and compute missing metrics. Returns list of full trace trees with computed metrics.",
    response_model=SessionTracesResponse,
    response_model_exclude_none=True,
    tags=["Sessions"],
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
) -> SessionTracesResponse:
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


# USER ENDPOINTS


@trace_api_routes.get(
    "/traces/users",
    summary="List User Metadata",
    description="Get user metadata with pagination and filtering. Returns aggregated user information across sessions and traces.",
    response_model=TraceUserListResponse,
    response_model_exclude_none=True,
    tags=["Users"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_users_metadata(
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
) -> TraceUserListResponse:
    """Get user metadata with pagination and filtering."""
    try:
        span_repo = _get_span_repository(db_session)
        count, user_metadata_list = span_repo.get_users_metadata(
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            pagination_parameters=pagination_parameters,
        )

        users = [
            user_metadata._to_metadata_response_model()
            for user_metadata in user_metadata_list
        ]
        return TraceUserListResponse(count=count, users=users)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing user metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@trace_api_routes.get(
    "/traces/users/{user_id}",
    summary="Get User Details",
    description="Get detailed information for a single user including session and trace metadata.",
    response_model=TraceUserMetadataResponse,
    response_model_exclude_none=True,
    tags=["Users"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_user_details(
    user_id: str,
    task_ids: list[str] = Query(
        ...,
        description="Task IDs to filter on. At least one is required.",
        min_length=1,
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TraceUserMetadataResponse:
    """Get detailed information for a single user."""
    try:
        span_repo = _get_span_repository(db_session)
        user_details = span_repo.get_user_details(
            user_id=user_id,
            task_ids=task_ids,
        )

        if not user_details:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found or has no data",
            )

        return user_details._to_metadata_response_model()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


### TRACE ID-BASED ENDPOINTS


@trace_api_routes.get(
    "/traces/{trace_id}",
    summary="Get Single Trace",
    description="Get complete trace tree with existing metrics (no computation). Returns full trace structure with spans.",
    response_model=TraceResponse,
    response_model_exclude_none=True,
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_trace_by_id(
    trace_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TraceResponse:
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

        return trace
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace by id: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@trace_api_routes.get(
    "/traces/{trace_id}/metrics",
    summary="Compute Missing Trace Metrics",
    description="Compute all missing metrics for trace spans on-demand. Returns full trace tree with computed metrics.",
    response_model=TraceResponse,
    response_model_exclude_none=True,
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def compute_trace_metrics(
    trace_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TraceResponse:
    """Compute all missing metrics for trace spans on-demand."""
    try:
        span_repo = _get_span_repository(db_session)
        trace = span_repo.compute_trace_metrics(
            trace_id=trace_id,
        )

        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        return trace
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing trace metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@trace_api_routes.get(
    "/traces/annotations/{annotation_id}",
    summary="Get an annotation by id",
    description="Get an annotation by id",
    response_model=AgenticAnnotationResponse,
    response_model_exclude_none=True,
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_annotation_by_id(
    annotation_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> AgenticAnnotationResponse:
    """Annotate a trace with a score and description (1 = liked, 0 = disliked)."""
    try:
        span_repo = _get_span_repository(db_session)
        annotation = span_repo.get_annotation_by_id(
            annotation_id=annotation_id,
        )

        if not annotation:
            raise HTTPException(
                status_code=404,
                detail=f"Annotation {annotation_id} not found",
            )

        return annotation.to_response_model()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@trace_api_routes.get(
    "/traces/{trace_id}/annotations",
    summary="List Annotations for a Trace",
    description="List annotations for a trace",
    response_model=ListAgenticAnnotationsResponse,
    response_model_exclude_none=True,
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def list_annotations_for_trace(
    trace_id: str,
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        AgenticAnnotationListFilterRequest,
        Depends(AgenticAnnotationListFilterRequest.from_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ListAgenticAnnotationsResponse:
    """Annotate a trace with a score and description (1 = liked, 0 = disliked)."""
    try:
        span_repo = _get_span_repository(db_session)
        annotations = span_repo.list_annotations_for_trace(
            trace_id=trace_id,
            pagination_parameters=pagination_parameters,
            filter_request=filter_request,
        )
        return ListAgenticAnnotationsResponse(
            annotations=[annotation.to_response_model() for annotation in annotations],
            count=len(annotations),
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error annotating trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trace_api_routes.post(
    "/traces/{trace_id}/annotations",
    summary="Annotate a Trace",
    description="Annotate a trace with a score and description (1 = liked, 0 = disliked)",
    response_model=AgenticAnnotationResponse,
    response_model_exclude_none=True,
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def annotate_trace(
    trace_id: str,
    annotation_request: AgenticAnnotationRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> AgenticAnnotationResponse:
    """Annotate a trace with a score and description (1 = liked, 0 = disliked)."""
    try:
        span_repo = _get_span_repository(db_session)
        return span_repo.annotate_trace(
            trace_id=trace_id,
            annotation_request=annotation_request,
        ).to_response_model()
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error annotating trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trace_api_routes.delete(
    "/traces/{trace_id}/annotations",
    summary="Delete an annotation from a trace",
    description="Delete an annotation from a trace",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Annotation deleted from trace."},
    },
    tags=["Traces"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def delete_annotation_from_trace(
    trace_id: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """Delete an annotation from a trace."""
    try:
        span_repo = _get_span_repository(db_session)
        span_repo.delete_annotation_from_trace(
            trace_id=trace_id,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error annotating trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
