from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.list_rag_search_setting_configurations_response import ListRagSearchSettingConfigurationsResponse
from ...models.pagination_sort_method import PaginationSortMethod
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    *,
    config_name: None | str | Unset = UNSET,
    rag_provider_ids: list[UUID] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_config_name: None | str | Unset
    if isinstance(config_name, Unset):
        json_config_name = UNSET
    else:
        json_config_name = config_name
    params["config_name"] = json_config_name

    json_rag_provider_ids: list[str] | None | Unset
    if isinstance(rag_provider_ids, Unset):
        json_rag_provider_ids = UNSET
    elif isinstance(rag_provider_ids, list):
        json_rag_provider_ids = []
        for rag_provider_ids_type_0_item_data in rag_provider_ids:
            rag_provider_ids_type_0_item = str(rag_provider_ids_type_0_item_data)
            json_rag_provider_ids.append(rag_provider_ids_type_0_item)


    else:
        json_rag_provider_ids = rag_provider_ids
    params["rag_provider_ids"] = json_rag_provider_ids

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/tasks/{task_id}/rag_search_settings".format(task_id=quote(str(task_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ListRagSearchSettingConfigurationsResponse | None:
    if response.status_code == 200:
        response_200 = ListRagSearchSettingConfigurationsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ListRagSearchSettingConfigurationsResponse]:
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
    config_name: None | str | Unset = UNSET,
    rag_provider_ids: list[UUID] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | ListRagSearchSettingConfigurationsResponse]:
    """ Get Task Rag Search Settings

     Get list of RAG search setting configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): Rag search setting configuration name substring to
            search for.
        rag_provider_ids (list[UUID] | None | Unset): List of rag provider configuration IDs to
            filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListRagSearchSettingConfigurationsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
config_name=config_name,
rag_provider_ids=rag_provider_ids,
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
    config_name: None | str | Unset = UNSET,
    rag_provider_ids: list[UUID] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | ListRagSearchSettingConfigurationsResponse | None:
    """ Get Task Rag Search Settings

     Get list of RAG search setting configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): Rag search setting configuration name substring to
            search for.
        rag_provider_ids (list[UUID] | None | Unset): List of rag provider configuration IDs to
            filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListRagSearchSettingConfigurationsResponse
     """


    return sync_detailed(
        task_id=task_id,
client=client,
config_name=config_name,
rag_provider_ids=rag_provider_ids,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    config_name: None | str | Unset = UNSET,
    rag_provider_ids: list[UUID] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | ListRagSearchSettingConfigurationsResponse]:
    """ Get Task Rag Search Settings

     Get list of RAG search setting configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): Rag search setting configuration name substring to
            search for.
        rag_provider_ids (list[UUID] | None | Unset): List of rag provider configuration IDs to
            filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListRagSearchSettingConfigurationsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
config_name=config_name,
rag_provider_ids=rag_provider_ids,
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
    config_name: None | str | Unset = UNSET,
    rag_provider_ids: list[UUID] | None | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | ListRagSearchSettingConfigurationsResponse | None:
    """ Get Task Rag Search Settings

     Get list of RAG search setting configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): Rag search setting configuration name substring to
            search for.
        rag_provider_ids (list[UUID] | None | Unset): List of rag provider configuration IDs to
            filter for.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListRagSearchSettingConfigurationsResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
config_name=config_name,
rag_provider_ids=rag_provider_ids,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
