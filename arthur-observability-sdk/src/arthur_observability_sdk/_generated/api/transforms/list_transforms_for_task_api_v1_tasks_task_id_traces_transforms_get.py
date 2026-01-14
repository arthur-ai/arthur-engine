from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.list_trace_transforms_response import ListTraceTransformsResponse
from ...models.pagination_sort_method import PaginationSortMethod
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    *,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page

    json_name: None | str | Unset
    if isinstance(name, Unset):
        json_name = UNSET
    else:
        json_name = name
    params["name"] = json_name

    json_created_after: None | str | Unset
    if isinstance(created_after, Unset):
        json_created_after = UNSET
    else:
        json_created_after = created_after
    params["created_after"] = json_created_after

    json_created_before: None | str | Unset
    if isinstance(created_before, Unset):
        json_created_before = UNSET
    else:
        json_created_before = created_before
    params["created_before"] = json_created_before


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/tasks/{task_id}/traces/transforms".format(task_id=quote(str(task_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ListTraceTransformsResponse | None:
    if response.status_code == 200:
        response_200 = ListTraceTransformsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ListTraceTransformsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> Response[HTTPValidationError | ListTraceTransformsResponse]:
    """ List Transforms For Task

     List all transforms for a task.

    Args:
        task_id (UUID):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        name (None | str | Unset): Name of the transform to filter on using partial matching.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListTraceTransformsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
sort=sort,
page_size=page_size,
page=page,
name=name,
created_after=created_after,
created_before=created_before,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> HTTPValidationError | ListTraceTransformsResponse | None:
    """ List Transforms For Task

     List all transforms for a task.

    Args:
        task_id (UUID):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        name (None | str | Unset): Name of the transform to filter on using partial matching.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListTraceTransformsResponse
     """


    return sync_detailed(
        task_id=task_id,
client=client,
sort=sort,
page_size=page_size,
page=page,
name=name,
created_after=created_after,
created_before=created_before,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> Response[HTTPValidationError | ListTraceTransformsResponse]:
    """ List Transforms For Task

     List all transforms for a task.

    Args:
        task_id (UUID):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        name (None | str | Unset): Name of the transform to filter on using partial matching.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListTraceTransformsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
sort=sort,
page_size=page_size,
page=page,
name=name,
created_after=created_after,
created_before=created_before,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> HTTPValidationError | ListTraceTransformsResponse | None:
    """ List Transforms For Task

     List all transforms for a task.

    Args:
        task_id (UUID):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        name (None | str | Unset): Name of the transform to filter on using partial matching.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListTraceTransformsResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
sort=sort,
page_size=page_size,
page=page,
name=name,
created_after=created_after,
created_before=created_before,

    )).parsed
