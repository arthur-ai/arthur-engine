from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.prompt_experiment_list_response import PromptExperimentListResponse
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    *,
    search: None | str | Unset = UNSET,
    dataset_id: None | Unset | UUID = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_search: None | str | Unset
    if isinstance(search, Unset):
        json_search = UNSET
    else:
        json_search = search
    params["search"] = json_search

    json_dataset_id: None | str | Unset
    if isinstance(dataset_id, Unset):
        json_dataset_id = UNSET
    elif isinstance(dataset_id, UUID):
        json_dataset_id = str(dataset_id)
    else:
        json_dataset_id = dataset_id
    params["dataset_id"] = json_dataset_id

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/tasks/{task_id}/prompt_experiments".format(task_id=quote(str(task_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | PromptExperimentListResponse | None:
    if response.status_code == 200:
        response_200 = PromptExperimentListResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | PromptExperimentListResponse]:
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
    search: None | str | Unset = UNSET,
    dataset_id: None | Unset | UUID = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | PromptExperimentListResponse]:
    """ List prompt experiments

     List all prompt experiments for a task with optional filtering and pagination

    Args:
        task_id (UUID):
        search (None | str | Unset): Search text to filter experiments by name, description,
            prompt name, or dataset name
        dataset_id (None | Unset | UUID): Filter experiments by dataset ID
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptExperimentListResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
search=search,
dataset_id=dataset_id,
sort=sort,
page_size=page_size,
page=page,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    search: None | str | Unset = UNSET,
    dataset_id: None | Unset | UUID = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | PromptExperimentListResponse | None:
    """ List prompt experiments

     List all prompt experiments for a task with optional filtering and pagination

    Args:
        task_id (UUID):
        search (None | str | Unset): Search text to filter experiments by name, description,
            prompt name, or dataset name
        dataset_id (None | Unset | UUID): Filter experiments by dataset ID
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptExperimentListResponse
     """


    return sync_detailed(
        task_id=task_id,
client=client,
search=search,
dataset_id=dataset_id,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    search: None | str | Unset = UNSET,
    dataset_id: None | Unset | UUID = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | PromptExperimentListResponse]:
    """ List prompt experiments

     List all prompt experiments for a task with optional filtering and pagination

    Args:
        task_id (UUID):
        search (None | str | Unset): Search text to filter experiments by name, description,
            prompt name, or dataset name
        dataset_id (None | Unset | UUID): Filter experiments by dataset ID
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptExperimentListResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
search=search,
dataset_id=dataset_id,
sort=sort,
page_size=page_size,
page=page,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    search: None | str | Unset = UNSET,
    dataset_id: None | Unset | UUID = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | PromptExperimentListResponse | None:
    """ List prompt experiments

     List all prompt experiments for a task with optional filtering and pagination

    Args:
        task_id (UUID):
        search (None | str | Unset): Search text to filter experiments by name, description,
            prompt name, or dataset name
        dataset_id (None | Unset | UUID): Filter experiments by dataset ID
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptExperimentListResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
search=search,
dataset_id=dataset_id,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
