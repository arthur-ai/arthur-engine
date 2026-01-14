from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.search_datasets_response import SearchDatasetsResponse
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    *,
    dataset_ids: list[UUID] | None | Unset = UNSET,
    dataset_name: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_dataset_ids: list[str] | None | Unset
    if isinstance(dataset_ids, Unset):
        json_dataset_ids = UNSET
    elif isinstance(dataset_ids, list):
        json_dataset_ids = []
        for dataset_ids_type_0_item_data in dataset_ids:
            dataset_ids_type_0_item = str(dataset_ids_type_0_item_data)
            json_dataset_ids.append(dataset_ids_type_0_item)


    else:
        json_dataset_ids = dataset_ids
    params["dataset_ids"] = json_dataset_ids

    json_dataset_name: None | str | Unset
    if isinstance(dataset_name, Unset):
        json_dataset_name = UNSET
    else:
        json_dataset_name = dataset_name
    params["dataset_name"] = json_dataset_name

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/tasks/{task_id}/datasets/search".format(task_id=quote(str(task_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | SearchDatasetsResponse | None:
    if response.status_code == 200:
        response_200 = SearchDatasetsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | SearchDatasetsResponse]:
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
    dataset_ids: list[UUID] | None | Unset = UNSET,
    dataset_name: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | SearchDatasetsResponse]:
    """ Get Datasets

     Search datasets. Optionally can filter by dataset IDs and dataset name.

    Args:
        task_id (UUID):
        dataset_ids (list[UUID] | None | Unset): List of dataset ids to query for.
        dataset_name (None | str | Unset): Dataset name substring to search for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchDatasetsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
dataset_ids=dataset_ids,
dataset_name=dataset_name,
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
    dataset_ids: list[UUID] | None | Unset = UNSET,
    dataset_name: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | SearchDatasetsResponse | None:
    """ Get Datasets

     Search datasets. Optionally can filter by dataset IDs and dataset name.

    Args:
        task_id (UUID):
        dataset_ids (list[UUID] | None | Unset): List of dataset ids to query for.
        dataset_name (None | str | Unset): Dataset name substring to search for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchDatasetsResponse
     """


    return sync_detailed(
        task_id=task_id,
client=client,
dataset_ids=dataset_ids,
dataset_name=dataset_name,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    dataset_ids: list[UUID] | None | Unset = UNSET,
    dataset_name: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | SearchDatasetsResponse]:
    """ Get Datasets

     Search datasets. Optionally can filter by dataset IDs and dataset name.

    Args:
        task_id (UUID):
        dataset_ids (list[UUID] | None | Unset): List of dataset ids to query for.
        dataset_name (None | str | Unset): Dataset name substring to search for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchDatasetsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
dataset_ids=dataset_ids,
dataset_name=dataset_name,
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
    dataset_ids: list[UUID] | None | Unset = UNSET,
    dataset_name: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | SearchDatasetsResponse | None:
    """ Get Datasets

     Search datasets. Optionally can filter by dataset IDs and dataset name.

    Args:
        task_id (UUID):
        dataset_ids (list[UUID] | None | Unset): List of dataset ids to query for.
        dataset_name (None | str | Unset): Dataset name substring to search for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchDatasetsResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
dataset_ids=dataset_ids,
dataset_name=dataset_name,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
