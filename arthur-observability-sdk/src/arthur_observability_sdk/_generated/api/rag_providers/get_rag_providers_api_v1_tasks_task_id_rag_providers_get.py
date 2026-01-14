from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.rag_api_key_authentication_provider_enum import RagAPIKeyAuthenticationProviderEnum
from ...models.rag_provider_authentication_method_enum import RagProviderAuthenticationMethodEnum
from ...models.search_rag_provider_configurations_response import SearchRagProviderConfigurationsResponse
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    *,
    config_name: None | str | Unset = UNSET,
    authentication_method: None | RagProviderAuthenticationMethodEnum | Unset = UNSET,
    rag_provider_name: None | RagAPIKeyAuthenticationProviderEnum | Unset = UNSET,
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

    json_authentication_method: None | str | Unset
    if isinstance(authentication_method, Unset):
        json_authentication_method = UNSET
    elif isinstance(authentication_method, RagProviderAuthenticationMethodEnum):
        json_authentication_method = authentication_method.value
    else:
        json_authentication_method = authentication_method
    params["authentication_method"] = json_authentication_method

    json_rag_provider_name: None | str | Unset
    if isinstance(rag_provider_name, Unset):
        json_rag_provider_name = UNSET
    elif isinstance(rag_provider_name, RagAPIKeyAuthenticationProviderEnum):
        json_rag_provider_name = rag_provider_name.value
    else:
        json_rag_provider_name = rag_provider_name
    params["rag_provider_name"] = json_rag_provider_name

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/tasks/{task_id}/rag_providers".format(task_id=quote(str(task_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | SearchRagProviderConfigurationsResponse | None:
    if response.status_code == 200:
        response_200 = SearchRagProviderConfigurationsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | SearchRagProviderConfigurationsResponse]:
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
    authentication_method: None | RagProviderAuthenticationMethodEnum | Unset = UNSET,
    rag_provider_name: None | RagAPIKeyAuthenticationProviderEnum | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | SearchRagProviderConfigurationsResponse]:
    """ Get Rag Providers

     Get list of RAG provider connection configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): RAG Provider configuration name substring to search for.
        authentication_method (None | RagProviderAuthenticationMethodEnum | Unset): RAG Provider
            authentication method to filter by.
        rag_provider_name (None | RagAPIKeyAuthenticationProviderEnum | Unset): RAG provider name
            to filter by.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchRagProviderConfigurationsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
config_name=config_name,
authentication_method=authentication_method,
rag_provider_name=rag_provider_name,
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
    authentication_method: None | RagProviderAuthenticationMethodEnum | Unset = UNSET,
    rag_provider_name: None | RagAPIKeyAuthenticationProviderEnum | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | SearchRagProviderConfigurationsResponse | None:
    """ Get Rag Providers

     Get list of RAG provider connection configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): RAG Provider configuration name substring to search for.
        authentication_method (None | RagProviderAuthenticationMethodEnum | Unset): RAG Provider
            authentication method to filter by.
        rag_provider_name (None | RagAPIKeyAuthenticationProviderEnum | Unset): RAG provider name
            to filter by.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchRagProviderConfigurationsResponse
     """


    return sync_detailed(
        task_id=task_id,
client=client,
config_name=config_name,
authentication_method=authentication_method,
rag_provider_name=rag_provider_name,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    config_name: None | str | Unset = UNSET,
    authentication_method: None | RagProviderAuthenticationMethodEnum | Unset = UNSET,
    rag_provider_name: None | RagAPIKeyAuthenticationProviderEnum | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | SearchRagProviderConfigurationsResponse]:
    """ Get Rag Providers

     Get list of RAG provider connection configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): RAG Provider configuration name substring to search for.
        authentication_method (None | RagProviderAuthenticationMethodEnum | Unset): RAG Provider
            authentication method to filter by.
        rag_provider_name (None | RagAPIKeyAuthenticationProviderEnum | Unset): RAG provider name
            to filter by.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchRagProviderConfigurationsResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
config_name=config_name,
authentication_method=authentication_method,
rag_provider_name=rag_provider_name,
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
    authentication_method: None | RagProviderAuthenticationMethodEnum | Unset = UNSET,
    rag_provider_name: None | RagAPIKeyAuthenticationProviderEnum | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | SearchRagProviderConfigurationsResponse | None:
    """ Get Rag Providers

     Get list of RAG provider connection configurations for the task.

    Args:
        task_id (UUID): ID of the task to fetch the provider connections for.
        config_name (None | str | Unset): RAG Provider configuration name substring to search for.
        authentication_method (None | RagProviderAuthenticationMethodEnum | Unset): RAG Provider
            authentication method to filter by.
        rag_provider_name (None | RagAPIKeyAuthenticationProviderEnum | Unset): RAG provider name
            to filter by.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchRagProviderConfigurationsResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
config_name=config_name,
authentication_method=authentication_method,
rag_provider_name=rag_provider_name,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
