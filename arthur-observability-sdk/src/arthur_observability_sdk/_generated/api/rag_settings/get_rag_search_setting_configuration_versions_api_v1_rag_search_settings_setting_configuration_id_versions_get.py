from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.list_rag_search_setting_configuration_versions_response import ListRagSearchSettingConfigurationVersionsResponse
from ...models.pagination_sort_method import PaginationSortMethod
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    setting_configuration_id: UUID,
    *,
    tags: list[str] | None | Unset = UNSET,
    version_numbers: list[int] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_tags: list[str] | None | Unset
    if isinstance(tags, Unset):
        json_tags = UNSET
    elif isinstance(tags, list):
        json_tags = tags


    else:
        json_tags = tags
    params["tags"] = json_tags

    json_version_numbers: list[int] | None | Unset
    if isinstance(version_numbers, Unset):
        json_version_numbers = UNSET
    elif isinstance(version_numbers, list):
        json_version_numbers = version_numbers


    else:
        json_version_numbers = version_numbers
    params["version_numbers"] = json_version_numbers

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/rag_search_settings/{setting_configuration_id}/versions".format(setting_configuration_id=quote(str(setting_configuration_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse | None:
    if response.status_code == 200:
        response_200 = ListRagSearchSettingConfigurationVersionsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    setting_configuration_id: UUID,
    *,
    client: AuthenticatedClient,
    tags: list[str] | None | Unset = UNSET,
    version_numbers: list[int] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse]:
    """ Get Rag Search Setting Configuration Versions

     Get list of versions for the RAG search setting configuration.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to get
            versions for.
        tags (list[str] | None | Unset): List of tags to filter for versions tagged with any
            matching tag.
        version_numbers (list[int] | None | Unset): List of version numbers to filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,
tags=tags,
version_numbers=version_numbers,
sort=sort,
page_size=page_size,
page=page,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    setting_configuration_id: UUID,
    *,
    client: AuthenticatedClient,
    tags: list[str] | None | Unset = UNSET,
    version_numbers: list[int] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse | None:
    """ Get Rag Search Setting Configuration Versions

     Get list of versions for the RAG search setting configuration.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to get
            versions for.
        tags (list[str] | None | Unset): List of tags to filter for versions tagged with any
            matching tag.
        version_numbers (list[int] | None | Unset): List of version numbers to filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse
     """


    return sync_detailed(
        setting_configuration_id=setting_configuration_id,
client=client,
tags=tags,
version_numbers=version_numbers,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    setting_configuration_id: UUID,
    *,
    client: AuthenticatedClient,
    tags: list[str] | None | Unset = UNSET,
    version_numbers: list[int] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse]:
    """ Get Rag Search Setting Configuration Versions

     Get list of versions for the RAG search setting configuration.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to get
            versions for.
        tags (list[str] | None | Unset): List of tags to filter for versions tagged with any
            matching tag.
        version_numbers (list[int] | None | Unset): List of version numbers to filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,
tags=tags,
version_numbers=version_numbers,
sort=sort,
page_size=page_size,
page=page,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    setting_configuration_id: UUID,
    *,
    client: AuthenticatedClient,
    tags: list[str] | None | Unset = UNSET,
    version_numbers: list[int] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse | None:
    """ Get Rag Search Setting Configuration Versions

     Get list of versions for the RAG search setting configuration.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to get
            versions for.
        tags (list[str] | None | Unset): List of tags to filter for versions tagged with any
            matching tag.
        version_numbers (list[int] | None | Unset): List of version numbers to filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListRagSearchSettingConfigurationVersionsResponse
     """


    return (await asyncio_detailed(
        setting_configuration_id=setting_configuration_id,
client=client,
tags=tags,
version_numbers=version_numbers,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
