import logging
from datetime import datetime
from typing import Annotated

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.request_schemas import TraceQueryRequest
from arthur_common.models.response_schemas import (
    SpanWithMetricsResponse,
    TraceResponse,
)
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from google.protobuf.message import DecodeError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from dependencies import get_db_session
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v1.legacy_span_routes import _create_response, trace_query_parameters
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from schemas.response_schemas import (
    SessionListResponse,
    SessionTracesResponse,
    SpanListResponse,
    TraceListResponse,
    UserListResponse,
    UserSessionsResponse,
    UserTracesResponse,
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


@trace_api_routes.get(
    "/traces",
    summary="List Trace Metadata",
    description="Get lightweight trace metadata for browsing/filtering operations. Returns metadata only without spans or metrics for fast performance.",
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
):
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


# SPAN ENDPOINTS


@trace_api_routes.get(
    "/spans",
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
    trace_query: Annotated[
        TraceQueryRequest,
        Depends(trace_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
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
            filters=trace_query,  # Enables comprehensive filtering
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


@trace_api_routes.get(
    "/spans/{span_id}",
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


@trace_api_routes.get(
    "/spans/{span_id}/metrics",
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
):
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
    "/sessions",
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


@trace_api_routes.get(
    "/sessions/{session_id}",
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
):
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
    "/sessions/{session_id}/metrics",
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


# USER ENDPOINTS


@trace_api_routes.get(
    "/users",
    summary="List User Metadata",
    description="Get user metadata with pagination and filtering. Returns aggregated user information across sessions and traces.",
    response_model=UserListResponse,
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
):
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
        return UserListResponse(count=count, users=users)
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
    "/users/{user_id}/sessions",
    summary="Get User Sessions",
    description="Get all sessions for a user. Returns list of session metadata for the specified user.",
    response_model=UserSessionsResponse,
    response_model_exclude_none=True,
    tags=["Users"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_user_sessions(
    user_id: str,
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get all sessions for a user."""
    try:
        span_repo = _get_span_repository(db_session)
        count, user_sessions = span_repo.get_user_sessions(
            user_id=user_id,
            pagination_parameters=pagination_parameters,
        )

        session_responses = [
            session._to_metadata_response_model() for session in user_sessions
        ]

        return UserSessionsResponse(
            user_id=user_id,
            count=count,
            sessions=session_responses,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@trace_api_routes.get(
    "/users/{user_id}/traces",
    summary="Get User Traces",
    description="Get all traces for a user. Returns list of trace metadata for the specified user, including traces not associated with sessions.",
    response_model=UserTracesResponse,
    response_model_exclude_none=True,
    tags=["Users"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def get_user_traces(
    user_id: str,
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Get all traces for a user."""
    try:
        span_repo = _get_span_repository(db_session)
        count, user_traces = span_repo.get_user_traces(
            user_id=user_id,
            pagination_parameters=pagination_parameters,
        )

        trace_responses = [trace._to_metadata_response_model() for trace in user_traces]

        return UserTracesResponse(
            user_id=user_id,
            count=count,
            traces=trace_responses,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
