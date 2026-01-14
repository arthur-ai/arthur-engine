from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.agentic_annotation_type import AgenticAnnotationType
from ...models.continuous_eval_run_status import ContinuousEvalRunStatus
from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.span_list_response import SpanListResponse
from ...models.tool_class_enum import ToolClassEnum
from ...types import UNSET, Unset
from dateutil.parser import isoparse
from typing import cast
import datetime



def _get_kwargs(
    *,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    task_ids: list[str],
    trace_ids: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    tool_name: str | Unset = UNSET,
    span_types: list[str] | Unset = UNSET,
    annotation_score: int | Unset = UNSET,
    annotation_type: AgenticAnnotationType | Unset = UNSET,
    continuous_eval_run_status: ContinuousEvalRunStatus | Unset = UNSET,
    continuous_eval_name: str | Unset = UNSET,
    span_ids: list[str] | Unset = UNSET,
    session_ids: list[str] | Unset = UNSET,
    user_ids: list[str] | Unset = UNSET,
    span_name: str | Unset = UNSET,
    span_name_contains: str | Unset = UNSET,
    status_code: list[str] | Unset = UNSET,
    query_relevance_eq: float | Unset = UNSET,
    query_relevance_gt: float | Unset = UNSET,
    query_relevance_gte: float | Unset = UNSET,
    query_relevance_lt: float | Unset = UNSET,
    query_relevance_lte: float | Unset = UNSET,
    response_relevance_eq: float | Unset = UNSET,
    response_relevance_gt: float | Unset = UNSET,
    response_relevance_gte: float | Unset = UNSET,
    response_relevance_lt: float | Unset = UNSET,
    response_relevance_lte: float | Unset = UNSET,
    tool_selection: ToolClassEnum | Unset = UNSET,
    tool_usage: ToolClassEnum | Unset = UNSET,
    trace_duration_eq: float | Unset = UNSET,
    trace_duration_gt: float | Unset = UNSET,
    trace_duration_gte: float | Unset = UNSET,
    trace_duration_lt: float | Unset = UNSET,
    trace_duration_lte: float | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page

    json_task_ids = task_ids


    params["task_ids"] = json_task_ids

    json_trace_ids: list[str] | Unset = UNSET
    if not isinstance(trace_ids, Unset):
        json_trace_ids = trace_ids


    params["trace_ids"] = json_trace_ids

    json_start_time: str | Unset = UNSET
    if not isinstance(start_time, Unset):
        json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time: str | Unset = UNSET
    if not isinstance(end_time, Unset):
        json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    params["tool_name"] = tool_name

    json_span_types: list[str] | Unset = UNSET
    if not isinstance(span_types, Unset):
        json_span_types = span_types


    params["span_types"] = json_span_types

    params["annotation_score"] = annotation_score

    json_annotation_type: str | Unset = UNSET
    if not isinstance(annotation_type, Unset):
        json_annotation_type = annotation_type.value

    params["annotation_type"] = json_annotation_type

    json_continuous_eval_run_status: str | Unset = UNSET
    if not isinstance(continuous_eval_run_status, Unset):
        json_continuous_eval_run_status = continuous_eval_run_status.value

    params["continuous_eval_run_status"] = json_continuous_eval_run_status

    params["continuous_eval_name"] = continuous_eval_name

    json_span_ids: list[str] | Unset = UNSET
    if not isinstance(span_ids, Unset):
        json_span_ids = span_ids


    params["span_ids"] = json_span_ids

    json_session_ids: list[str] | Unset = UNSET
    if not isinstance(session_ids, Unset):
        json_session_ids = session_ids


    params["session_ids"] = json_session_ids

    json_user_ids: list[str] | Unset = UNSET
    if not isinstance(user_ids, Unset):
        json_user_ids = user_ids


    params["user_ids"] = json_user_ids

    params["span_name"] = span_name

    params["span_name_contains"] = span_name_contains

    json_status_code: list[str] | Unset = UNSET
    if not isinstance(status_code, Unset):
        json_status_code = status_code


    params["status_code"] = json_status_code

    params["query_relevance_eq"] = query_relevance_eq

    params["query_relevance_gt"] = query_relevance_gt

    params["query_relevance_gte"] = query_relevance_gte

    params["query_relevance_lt"] = query_relevance_lt

    params["query_relevance_lte"] = query_relevance_lte

    params["response_relevance_eq"] = response_relevance_eq

    params["response_relevance_gt"] = response_relevance_gt

    params["response_relevance_gte"] = response_relevance_gte

    params["response_relevance_lt"] = response_relevance_lt

    params["response_relevance_lte"] = response_relevance_lte

    json_tool_selection: int | Unset = UNSET
    if not isinstance(tool_selection, Unset):
        json_tool_selection = tool_selection.value

    params["tool_selection"] = json_tool_selection

    json_tool_usage: int | Unset = UNSET
    if not isinstance(tool_usage, Unset):
        json_tool_usage = tool_usage.value

    params["tool_usage"] = json_tool_usage

    params["trace_duration_eq"] = trace_duration_eq

    params["trace_duration_gt"] = trace_duration_gt

    params["trace_duration_gte"] = trace_duration_gte

    params["trace_duration_lt"] = trace_duration_lt

    params["trace_duration_lte"] = trace_duration_lte


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/traces/spans",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | SpanListResponse | None:
    if response.status_code == 200:
        response_200 = SpanListResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | SpanListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    task_ids: list[str],
    trace_ids: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    tool_name: str | Unset = UNSET,
    span_types: list[str] | Unset = UNSET,
    annotation_score: int | Unset = UNSET,
    annotation_type: AgenticAnnotationType | Unset = UNSET,
    continuous_eval_run_status: ContinuousEvalRunStatus | Unset = UNSET,
    continuous_eval_name: str | Unset = UNSET,
    span_ids: list[str] | Unset = UNSET,
    session_ids: list[str] | Unset = UNSET,
    user_ids: list[str] | Unset = UNSET,
    span_name: str | Unset = UNSET,
    span_name_contains: str | Unset = UNSET,
    status_code: list[str] | Unset = UNSET,
    query_relevance_eq: float | Unset = UNSET,
    query_relevance_gt: float | Unset = UNSET,
    query_relevance_gte: float | Unset = UNSET,
    query_relevance_lt: float | Unset = UNSET,
    query_relevance_lte: float | Unset = UNSET,
    response_relevance_eq: float | Unset = UNSET,
    response_relevance_gt: float | Unset = UNSET,
    response_relevance_gte: float | Unset = UNSET,
    response_relevance_lt: float | Unset = UNSET,
    response_relevance_lte: float | Unset = UNSET,
    tool_selection: ToolClassEnum | Unset = UNSET,
    tool_usage: ToolClassEnum | Unset = UNSET,
    trace_duration_eq: float | Unset = UNSET,
    trace_duration_gt: float | Unset = UNSET,
    trace_duration_gte: float | Unset = UNSET,
    trace_duration_lt: float | Unset = UNSET,
    trace_duration_lte: float | Unset = UNSET,

) -> Response[HTTPValidationError | SpanListResponse]:
    """ List Span Metadata with Filtering

     Get lightweight span metadata with comprehensive filtering support. Returns individual spans that
    match filtering criteria with the same filtering capabilities as trace filtering. Supports trace-
    level filters, span-level filters, and metric filters.

    Args:
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        trace_ids (list[str] | Unset): Trace IDs to filter on. Optional.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        tool_name (str | Unset): Return only results with this tool name.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        annotation_score (int | Unset): Filter by trace annotation score (0 or 1).
        annotation_type (AgenticAnnotationType | Unset):
        continuous_eval_run_status (ContinuousEvalRunStatus | Unset):
        continuous_eval_name (str | Unset): Filter by continuous eval name.
        span_ids (list[str] | Unset): Span IDs to filter on. Optional.
        session_ids (list[str] | Unset): Session IDs to filter on. Optional.
        user_ids (list[str] | Unset): User IDs to filter on. Optional.
        span_name (str | Unset): Return only results with this span name.
        span_name_contains (str | Unset): Return only results where span name contains this
            substring.
        status_code (list[str] | Unset): Status codes to filter on. Optional. Valid values: Ok,
            Error, Unset.
        query_relevance_eq (float | Unset): Equal to this value.
        query_relevance_gt (float | Unset): Greater than this value.
        query_relevance_gte (float | Unset): Greater than or equal to this value.
        query_relevance_lt (float | Unset): Less than this value.
        query_relevance_lte (float | Unset): Less than or equal to this value.
        response_relevance_eq (float | Unset): Equal to this value.
        response_relevance_gt (float | Unset): Greater than this value.
        response_relevance_gte (float | Unset): Greater than or equal to this value.
        response_relevance_lt (float | Unset): Less than this value.
        response_relevance_lte (float | Unset): Less than or equal to this value.
        tool_selection (ToolClassEnum | Unset):
        tool_usage (ToolClassEnum | Unset):
        trace_duration_eq (float | Unset): Duration exactly equal to this value (seconds).
        trace_duration_gt (float | Unset): Duration greater than this value (seconds).
        trace_duration_gte (float | Unset): Duration greater than or equal to this value
            (seconds).
        trace_duration_lt (float | Unset): Duration less than this value (seconds).
        trace_duration_lte (float | Unset): Duration less than or equal to this value (seconds).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SpanListResponse]
     """


    kwargs = _get_kwargs(
        sort=sort,
page_size=page_size,
page=page,
task_ids=task_ids,
trace_ids=trace_ids,
start_time=start_time,
end_time=end_time,
tool_name=tool_name,
span_types=span_types,
annotation_score=annotation_score,
annotation_type=annotation_type,
continuous_eval_run_status=continuous_eval_run_status,
continuous_eval_name=continuous_eval_name,
span_ids=span_ids,
session_ids=session_ids,
user_ids=user_ids,
span_name=span_name,
span_name_contains=span_name_contains,
status_code=status_code,
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

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    task_ids: list[str],
    trace_ids: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    tool_name: str | Unset = UNSET,
    span_types: list[str] | Unset = UNSET,
    annotation_score: int | Unset = UNSET,
    annotation_type: AgenticAnnotationType | Unset = UNSET,
    continuous_eval_run_status: ContinuousEvalRunStatus | Unset = UNSET,
    continuous_eval_name: str | Unset = UNSET,
    span_ids: list[str] | Unset = UNSET,
    session_ids: list[str] | Unset = UNSET,
    user_ids: list[str] | Unset = UNSET,
    span_name: str | Unset = UNSET,
    span_name_contains: str | Unset = UNSET,
    status_code: list[str] | Unset = UNSET,
    query_relevance_eq: float | Unset = UNSET,
    query_relevance_gt: float | Unset = UNSET,
    query_relevance_gte: float | Unset = UNSET,
    query_relevance_lt: float | Unset = UNSET,
    query_relevance_lte: float | Unset = UNSET,
    response_relevance_eq: float | Unset = UNSET,
    response_relevance_gt: float | Unset = UNSET,
    response_relevance_gte: float | Unset = UNSET,
    response_relevance_lt: float | Unset = UNSET,
    response_relevance_lte: float | Unset = UNSET,
    tool_selection: ToolClassEnum | Unset = UNSET,
    tool_usage: ToolClassEnum | Unset = UNSET,
    trace_duration_eq: float | Unset = UNSET,
    trace_duration_gt: float | Unset = UNSET,
    trace_duration_gte: float | Unset = UNSET,
    trace_duration_lt: float | Unset = UNSET,
    trace_duration_lte: float | Unset = UNSET,

) -> HTTPValidationError | SpanListResponse | None:
    """ List Span Metadata with Filtering

     Get lightweight span metadata with comprehensive filtering support. Returns individual spans that
    match filtering criteria with the same filtering capabilities as trace filtering. Supports trace-
    level filters, span-level filters, and metric filters.

    Args:
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        trace_ids (list[str] | Unset): Trace IDs to filter on. Optional.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        tool_name (str | Unset): Return only results with this tool name.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        annotation_score (int | Unset): Filter by trace annotation score (0 or 1).
        annotation_type (AgenticAnnotationType | Unset):
        continuous_eval_run_status (ContinuousEvalRunStatus | Unset):
        continuous_eval_name (str | Unset): Filter by continuous eval name.
        span_ids (list[str] | Unset): Span IDs to filter on. Optional.
        session_ids (list[str] | Unset): Session IDs to filter on. Optional.
        user_ids (list[str] | Unset): User IDs to filter on. Optional.
        span_name (str | Unset): Return only results with this span name.
        span_name_contains (str | Unset): Return only results where span name contains this
            substring.
        status_code (list[str] | Unset): Status codes to filter on. Optional. Valid values: Ok,
            Error, Unset.
        query_relevance_eq (float | Unset): Equal to this value.
        query_relevance_gt (float | Unset): Greater than this value.
        query_relevance_gte (float | Unset): Greater than or equal to this value.
        query_relevance_lt (float | Unset): Less than this value.
        query_relevance_lte (float | Unset): Less than or equal to this value.
        response_relevance_eq (float | Unset): Equal to this value.
        response_relevance_gt (float | Unset): Greater than this value.
        response_relevance_gte (float | Unset): Greater than or equal to this value.
        response_relevance_lt (float | Unset): Less than this value.
        response_relevance_lte (float | Unset): Less than or equal to this value.
        tool_selection (ToolClassEnum | Unset):
        tool_usage (ToolClassEnum | Unset):
        trace_duration_eq (float | Unset): Duration exactly equal to this value (seconds).
        trace_duration_gt (float | Unset): Duration greater than this value (seconds).
        trace_duration_gte (float | Unset): Duration greater than or equal to this value
            (seconds).
        trace_duration_lt (float | Unset): Duration less than this value (seconds).
        trace_duration_lte (float | Unset): Duration less than or equal to this value (seconds).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SpanListResponse
     """


    return sync_detailed(
        client=client,
sort=sort,
page_size=page_size,
page=page,
task_ids=task_ids,
trace_ids=trace_ids,
start_time=start_time,
end_time=end_time,
tool_name=tool_name,
span_types=span_types,
annotation_score=annotation_score,
annotation_type=annotation_type,
continuous_eval_run_status=continuous_eval_run_status,
continuous_eval_name=continuous_eval_name,
span_ids=span_ids,
session_ids=session_ids,
user_ids=user_ids,
span_name=span_name,
span_name_contains=span_name_contains,
status_code=status_code,
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

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    task_ids: list[str],
    trace_ids: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    tool_name: str | Unset = UNSET,
    span_types: list[str] | Unset = UNSET,
    annotation_score: int | Unset = UNSET,
    annotation_type: AgenticAnnotationType | Unset = UNSET,
    continuous_eval_run_status: ContinuousEvalRunStatus | Unset = UNSET,
    continuous_eval_name: str | Unset = UNSET,
    span_ids: list[str] | Unset = UNSET,
    session_ids: list[str] | Unset = UNSET,
    user_ids: list[str] | Unset = UNSET,
    span_name: str | Unset = UNSET,
    span_name_contains: str | Unset = UNSET,
    status_code: list[str] | Unset = UNSET,
    query_relevance_eq: float | Unset = UNSET,
    query_relevance_gt: float | Unset = UNSET,
    query_relevance_gte: float | Unset = UNSET,
    query_relevance_lt: float | Unset = UNSET,
    query_relevance_lte: float | Unset = UNSET,
    response_relevance_eq: float | Unset = UNSET,
    response_relevance_gt: float | Unset = UNSET,
    response_relevance_gte: float | Unset = UNSET,
    response_relevance_lt: float | Unset = UNSET,
    response_relevance_lte: float | Unset = UNSET,
    tool_selection: ToolClassEnum | Unset = UNSET,
    tool_usage: ToolClassEnum | Unset = UNSET,
    trace_duration_eq: float | Unset = UNSET,
    trace_duration_gt: float | Unset = UNSET,
    trace_duration_gte: float | Unset = UNSET,
    trace_duration_lt: float | Unset = UNSET,
    trace_duration_lte: float | Unset = UNSET,

) -> Response[HTTPValidationError | SpanListResponse]:
    """ List Span Metadata with Filtering

     Get lightweight span metadata with comprehensive filtering support. Returns individual spans that
    match filtering criteria with the same filtering capabilities as trace filtering. Supports trace-
    level filters, span-level filters, and metric filters.

    Args:
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        trace_ids (list[str] | Unset): Trace IDs to filter on. Optional.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        tool_name (str | Unset): Return only results with this tool name.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        annotation_score (int | Unset): Filter by trace annotation score (0 or 1).
        annotation_type (AgenticAnnotationType | Unset):
        continuous_eval_run_status (ContinuousEvalRunStatus | Unset):
        continuous_eval_name (str | Unset): Filter by continuous eval name.
        span_ids (list[str] | Unset): Span IDs to filter on. Optional.
        session_ids (list[str] | Unset): Session IDs to filter on. Optional.
        user_ids (list[str] | Unset): User IDs to filter on. Optional.
        span_name (str | Unset): Return only results with this span name.
        span_name_contains (str | Unset): Return only results where span name contains this
            substring.
        status_code (list[str] | Unset): Status codes to filter on. Optional. Valid values: Ok,
            Error, Unset.
        query_relevance_eq (float | Unset): Equal to this value.
        query_relevance_gt (float | Unset): Greater than this value.
        query_relevance_gte (float | Unset): Greater than or equal to this value.
        query_relevance_lt (float | Unset): Less than this value.
        query_relevance_lte (float | Unset): Less than or equal to this value.
        response_relevance_eq (float | Unset): Equal to this value.
        response_relevance_gt (float | Unset): Greater than this value.
        response_relevance_gte (float | Unset): Greater than or equal to this value.
        response_relevance_lt (float | Unset): Less than this value.
        response_relevance_lte (float | Unset): Less than or equal to this value.
        tool_selection (ToolClassEnum | Unset):
        tool_usage (ToolClassEnum | Unset):
        trace_duration_eq (float | Unset): Duration exactly equal to this value (seconds).
        trace_duration_gt (float | Unset): Duration greater than this value (seconds).
        trace_duration_gte (float | Unset): Duration greater than or equal to this value
            (seconds).
        trace_duration_lt (float | Unset): Duration less than this value (seconds).
        trace_duration_lte (float | Unset): Duration less than or equal to this value (seconds).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SpanListResponse]
     """


    kwargs = _get_kwargs(
        sort=sort,
page_size=page_size,
page=page,
task_ids=task_ids,
trace_ids=trace_ids,
start_time=start_time,
end_time=end_time,
tool_name=tool_name,
span_types=span_types,
annotation_score=annotation_score,
annotation_type=annotation_type,
continuous_eval_run_status=continuous_eval_run_status,
continuous_eval_name=continuous_eval_name,
span_ids=span_ids,
session_ids=session_ids,
user_ids=user_ids,
span_name=span_name,
span_name_contains=span_name_contains,
status_code=status_code,
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

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    task_ids: list[str],
    trace_ids: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    tool_name: str | Unset = UNSET,
    span_types: list[str] | Unset = UNSET,
    annotation_score: int | Unset = UNSET,
    annotation_type: AgenticAnnotationType | Unset = UNSET,
    continuous_eval_run_status: ContinuousEvalRunStatus | Unset = UNSET,
    continuous_eval_name: str | Unset = UNSET,
    span_ids: list[str] | Unset = UNSET,
    session_ids: list[str] | Unset = UNSET,
    user_ids: list[str] | Unset = UNSET,
    span_name: str | Unset = UNSET,
    span_name_contains: str | Unset = UNSET,
    status_code: list[str] | Unset = UNSET,
    query_relevance_eq: float | Unset = UNSET,
    query_relevance_gt: float | Unset = UNSET,
    query_relevance_gte: float | Unset = UNSET,
    query_relevance_lt: float | Unset = UNSET,
    query_relevance_lte: float | Unset = UNSET,
    response_relevance_eq: float | Unset = UNSET,
    response_relevance_gt: float | Unset = UNSET,
    response_relevance_gte: float | Unset = UNSET,
    response_relevance_lt: float | Unset = UNSET,
    response_relevance_lte: float | Unset = UNSET,
    tool_selection: ToolClassEnum | Unset = UNSET,
    tool_usage: ToolClassEnum | Unset = UNSET,
    trace_duration_eq: float | Unset = UNSET,
    trace_duration_gt: float | Unset = UNSET,
    trace_duration_gte: float | Unset = UNSET,
    trace_duration_lt: float | Unset = UNSET,
    trace_duration_lte: float | Unset = UNSET,

) -> HTTPValidationError | SpanListResponse | None:
    """ List Span Metadata with Filtering

     Get lightweight span metadata with comprehensive filtering support. Returns individual spans that
    match filtering criteria with the same filtering capabilities as trace filtering. Supports trace-
    level filters, span-level filters, and metric filters.

    Args:
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        trace_ids (list[str] | Unset): Trace IDs to filter on. Optional.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        tool_name (str | Unset): Return only results with this tool name.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        annotation_score (int | Unset): Filter by trace annotation score (0 or 1).
        annotation_type (AgenticAnnotationType | Unset):
        continuous_eval_run_status (ContinuousEvalRunStatus | Unset):
        continuous_eval_name (str | Unset): Filter by continuous eval name.
        span_ids (list[str] | Unset): Span IDs to filter on. Optional.
        session_ids (list[str] | Unset): Session IDs to filter on. Optional.
        user_ids (list[str] | Unset): User IDs to filter on. Optional.
        span_name (str | Unset): Return only results with this span name.
        span_name_contains (str | Unset): Return only results where span name contains this
            substring.
        status_code (list[str] | Unset): Status codes to filter on. Optional. Valid values: Ok,
            Error, Unset.
        query_relevance_eq (float | Unset): Equal to this value.
        query_relevance_gt (float | Unset): Greater than this value.
        query_relevance_gte (float | Unset): Greater than or equal to this value.
        query_relevance_lt (float | Unset): Less than this value.
        query_relevance_lte (float | Unset): Less than or equal to this value.
        response_relevance_eq (float | Unset): Equal to this value.
        response_relevance_gt (float | Unset): Greater than this value.
        response_relevance_gte (float | Unset): Greater than or equal to this value.
        response_relevance_lt (float | Unset): Less than this value.
        response_relevance_lte (float | Unset): Less than or equal to this value.
        tool_selection (ToolClassEnum | Unset):
        tool_usage (ToolClassEnum | Unset):
        trace_duration_eq (float | Unset): Duration exactly equal to this value (seconds).
        trace_duration_gt (float | Unset): Duration greater than this value (seconds).
        trace_duration_gte (float | Unset): Duration greater than or equal to this value
            (seconds).
        trace_duration_lt (float | Unset): Duration less than this value (seconds).
        trace_duration_lte (float | Unset): Duration less than or equal to this value (seconds).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SpanListResponse
     """


    return (await asyncio_detailed(
        client=client,
sort=sort,
page_size=page_size,
page=page,
task_ids=task_ids,
trace_ids=trace_ids,
start_time=start_time,
end_time=end_time,
tool_name=tool_name,
span_types=span_types,
annotation_score=annotation_score,
annotation_type=annotation_type,
continuous_eval_run_status=continuous_eval_run_status,
continuous_eval_name=continuous_eval_name,
span_ids=span_ids,
session_ids=session_ids,
user_ids=user_ids,
span_name=span_name,
span_name_contains=span_name_contains,
status_code=status_code,
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

    )).parsed
