import json
import logging
from datetime import datetime
from typing import Annotated

from dependencies import get_db_session
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from google.protobuf.message import DecodeError
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.metrics_repository import MetricRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.common_schemas import PaginationParameters
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from schemas.response_schemas import QuerySpansResponse
from sqlalchemy.orm import Session
from utils.users import permission_checker
from utils.utils import common_pagination_parameters


logger = logging.getLogger(__name__)

span_routes = APIRouter(
    prefix="/v1",
    route_class=GenaiEngineRoute,
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
    try:
        tasks_metrics_repo = TasksMetricsRepository(db_session)
        metrics_repo = MetricRepository(db_session)
        span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)
        span_results = span_repo.create_traces(body)
        return response_handler(*span_results)
    except DecodeError as e:
        logger.error(f"Failed to decode protobuf message: {e}")
        raise HTTPException(status_code=400, detail="Invalid protobuf message format")
    except Exception as e:
        logger.error(f"Error processing traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@span_routes.get(
    "/spans/query",
    description="Query spans with filters for trace_id, span_id, task_id, and creation_time",
    response_model=QuerySpansResponse,
    response_model_exclude_none=True,
    tags=["Spans"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def query_spans(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    trace_ids: list[str] = Query(
        None,
        description="Trace ID to filter on.",
    ),
    span_ids: list[str] = Query(
        None,
        description="Span ID to filter on.",
    ),
    task_ids: list[str] = Query(
        None,
        description="Task ID to filter on.",
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
    try:
        span_repo = SpanRepository(db_session, TasksMetricsRepository(db_session), MetricRepository(db_session))
        spans = span_repo.query_spans(
            trace_ids=trace_ids,
            span_ids=span_ids,
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            sort=pagination_parameters.sort,
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
        )
        spans = [span._to_response_model() for span in spans]
        return QuerySpansResponse(count=len(spans), spans=spans)
    except Exception as e:
        logger.error(f"Error querying spans: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


def response_handler(
    total_spans,
    accepted_spans,
    unnecessary_spans,
    rejected_spans,
    rejected_reasons,
):
    content = {
        "total_spans": total_spans,
        "accepted_spans": accepted_spans,
        "unnecessary_spans": unnecessary_spans,
        "rejected_spans": rejected_spans,
        "rejection_reasons": rejected_reasons,
    }
    status_value = None
    status_code = None

    if rejected_spans == 0:
        status_value = "success"
        status_code = status.HTTP_200_OK

    elif accepted_spans > 0:
        status_value = "partial_success"
        status_code = status.HTTP_206_PARTIAL_CONTENT

    else:
        status_value = "failure"
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    content["status"] = status_value
    return Response(
        content=json.dumps(content),
        status_code=status_code,
        media_type="application/json",
    )
