import json
import logging
from datetime import datetime
from typing import Annotated

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
from schemas.common_schemas import PaginationParameters
from schemas.enums import PermissionLevelsEnum, ToolClassEnum
from schemas.internal_schemas import User
from schemas.request_schemas import SpanQueryRequest, TraceQueryRequest
from schemas.response_schemas import (
    QuerySpansResponse,
    QueryTracesWithMetricsResponse,
    SpanWithMetricsResponse,
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
        description="Inclusive start date in ISO8601 string format.",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format.",
    ),
    tool_name: str = Query(
        None,
        description="Return only results with this tool name.",
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
        gt=0,
        description="Duration exactly equal to this value (seconds).",
    ),
    trace_duration_gt: float = Query(
        None,
        gt=0,
        description="Duration greater than this value (seconds).",
    ),
    trace_duration_gte: float = Query(
        None,
        gt=0,
        description="Duration greater than or equal to this value (seconds).",
    ),
    trace_duration_lt: float = Query(
        None,
        gt=0,
        description="Duration less than this value (seconds).",
    ),
    trace_duration_lte: float = Query(
        None,
        gt=0,
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
        description="Inclusive start date in ISO8601 string format.",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format.",
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
        spans = span_repo.query_spans(
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
            count=len(spans),
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


@span_routes.get(
    "/span/{span_id}/metrics",
    description="Compute metrics for a single span. Validates that the span is an LLM span.",
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
    """Compute metrics for a single span. Validates that the span is an LLM span."""
    try:
        span_repo = _get_span_repository(db_session)
        span = span_repo.query_span_by_span_id_with_metrics(span_id)

        # Return the single span with metrics
        return span._to_response_model()
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing span metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
