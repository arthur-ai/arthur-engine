from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.list_dataset_versions_response import ListDatasetVersionsResponse
from ...models.pagination_sort_method import PaginationSortMethod
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    dataset_id: UUID,
    *,
    latest_version_only: bool | Unset = False,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["latest_version_only"] = latest_version_only

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/datasets/{dataset_id}/versions".format(dataset_id=quote(str(dataset_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ListDatasetVersionsResponse | None:
    if response.status_code == 200:
        response_200 = ListDatasetVersionsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ListDatasetVersionsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,
    latest_version_only: bool | Unset = False,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | ListDatasetVersionsResponse]:
    """ Get Dataset Versions

     List dataset versions.

    Args:
        dataset_id (UUID): ID of the dataset to fetch versions for.
        latest_version_only (bool | Unset): Whether to only include the latest version for the
            dataset in the response. Defaults to False. Default: False.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListDatasetVersionsResponse]
     """


    kwargs = _get_kwargs(
        dataset_id=dataset_id,
latest_version_only=latest_version_only,
sort=sort,
page_size=page_size,
page=page,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,
    latest_version_only: bool | Unset = False,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | ListDatasetVersionsResponse | None:
    """ Get Dataset Versions

     List dataset versions.

    Args:
        dataset_id (UUID): ID of the dataset to fetch versions for.
        latest_version_only (bool | Unset): Whether to only include the latest version for the
            dataset in the response. Defaults to False. Default: False.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListDatasetVersionsResponse
     """


    return sync_detailed(
        dataset_id=dataset_id,
client=client,
latest_version_only=latest_version_only,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,
    latest_version_only: bool | Unset = False,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | ListDatasetVersionsResponse]:
    """ Get Dataset Versions

     List dataset versions.

    Args:
        dataset_id (UUID): ID of the dataset to fetch versions for.
        latest_version_only (bool | Unset): Whether to only include the latest version for the
            dataset in the response. Defaults to False. Default: False.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListDatasetVersionsResponse]
     """


    kwargs = _get_kwargs(
        dataset_id=dataset_id,
latest_version_only=latest_version_only,
sort=sort,
page_size=page_size,
page=page,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,
    latest_version_only: bool | Unset = False,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | ListDatasetVersionsResponse | None:
    """ Get Dataset Versions

     List dataset versions.

    Args:
        dataset_id (UUID): ID of the dataset to fetch versions for.
        latest_version_only (bool | Unset): Whether to only include the latest version for the
            dataset in the response. Defaults to False. Default: False.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListDatasetVersionsResponse
     """


    return (await asyncio_detailed(
        dataset_id=dataset_id,
client=client,
latest_version_only=latest_version_only,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
