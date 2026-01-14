from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.query_spans_response import QuerySpansResponse
from ...types import UNSET, Unset
from dateutil.parser import isoparse
from typing import cast
import datetime



def _get_kwargs(
    *,
    task_ids: list[str],
    span_types: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_task_ids = task_ids


    params["task_ids"] = json_task_ids

    json_span_types: list[str] | Unset = UNSET
    if not isinstance(span_types, Unset):
        json_span_types = span_types


    params["span_types"] = json_span_types

    json_start_time: str | Unset = UNSET
    if not isinstance(start_time, Unset):
        json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time: str | Unset = UNSET
    if not isinstance(end_time, Unset):
        json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/spans/query",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | HTTPValidationError | QuerySpansResponse | None:
    if response.status_code == 200:
        response_200 = QuerySpansResponse.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 404:
        response_404 = cast(Any, None)
        return response_404

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | HTTPValidationError | QuerySpansResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    task_ids: list[str],
    span_types: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[Any | HTTPValidationError | QuerySpansResponse]:
    """ Query Spans By Type

     Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics
    but does not compute new ones.

    Args:
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | QuerySpansResponse]
     """


    kwargs = _get_kwargs(
        task_ids=task_ids,
span_types=span_types,
start_time=start_time,
end_time=end_time,
sort=sort,
page_size=page_size,
page=page,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    task_ids: list[str],
    span_types: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Any | HTTPValidationError | QuerySpansResponse | None:
    """ Query Spans By Type

     Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics
    but does not compute new ones.

    Args:
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | QuerySpansResponse
     """


    return sync_detailed(
        client=client,
task_ids=task_ids,
span_types=span_types,
start_time=start_time,
end_time=end_time,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    task_ids: list[str],
    span_types: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[Any | HTTPValidationError | QuerySpansResponse]:
    """ Query Spans By Type

     Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics
    but does not compute new ones.

    Args:
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | QuerySpansResponse]
     """


    kwargs = _get_kwargs(
        task_ids=task_ids,
span_types=span_types,
start_time=start_time,
end_time=end_time,
sort=sort,
page_size=page_size,
page=page,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    task_ids: list[str],
    span_types: list[str] | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Any | HTTPValidationError | QuerySpansResponse | None:
    """ Query Spans By Type

     Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics
    but does not compute new ones.

    Args:
        task_ids (list[str]): Task IDs to filter on. At least one is required.
        span_types (list[str] | Unset): Span types to filter on. Optional. Valid values: AGENT,
            CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format. Use
            local time (not UTC).
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format. Use
            local time (not UTC).
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | QuerySpansResponse
     """


    return (await asyncio_detailed(
        client=client,
task_ids=task_ids,
span_types=span_types,
start_time=start_time,
end_time=end_time,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
