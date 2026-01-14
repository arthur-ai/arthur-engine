from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.rag_provider_configuration_response import RagProviderConfigurationResponse
from typing import cast
from uuid import UUID



def _get_kwargs(
    provider_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/rag_providers/{provider_id}".format(provider_id=quote(str(provider_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | RagProviderConfigurationResponse | None:
    if response.status_code == 200:
        response_200 = RagProviderConfigurationResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | RagProviderConfigurationResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    provider_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | RagProviderConfigurationResponse]:
    """ Get Rag Provider

     Get a single RAG provider connection configuration.

    Args:
        provider_id (UUID): ID of RAG provider configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagProviderConfigurationResponse]
     """


    kwargs = _get_kwargs(
        provider_id=provider_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    provider_id: UUID,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | RagProviderConfigurationResponse | None:
    """ Get Rag Provider

     Get a single RAG provider connection configuration.

    Args:
        provider_id (UUID): ID of RAG provider configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagProviderConfigurationResponse
     """


    return sync_detailed(
        provider_id=provider_id,
client=client,

    ).parsed

async def asyncio_detailed(
    provider_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | RagProviderConfigurationResponse]:
    """ Get Rag Provider

     Get a single RAG provider connection configuration.

    Args:
        provider_id (UUID): ID of RAG provider configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagProviderConfigurationResponse]
     """


    kwargs = _get_kwargs(
        provider_id=provider_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    provider_id: UUID,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | RagProviderConfigurationResponse | None:
    """ Get Rag Provider

     Get a single RAG provider connection configuration.

    Args:
        provider_id (UUID): ID of RAG provider configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagProviderConfigurationResponse
     """


    return (await asyncio_detailed(
        provider_id=provider_id,
client=client,

    )).parsed
