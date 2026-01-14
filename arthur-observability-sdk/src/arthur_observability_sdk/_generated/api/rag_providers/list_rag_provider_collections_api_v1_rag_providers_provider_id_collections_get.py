from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.search_rag_provider_collections_response import SearchRagProviderCollectionsResponse
from typing import cast
from uuid import UUID



def _get_kwargs(
    provider_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/rag_providers/{provider_id}/collections".format(provider_id=quote(str(provider_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | SearchRagProviderCollectionsResponse | None:
    if response.status_code == 200:
        response_200 = SearchRagProviderCollectionsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | SearchRagProviderCollectionsResponse]:
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

) -> Response[HTTPValidationError | SearchRagProviderCollectionsResponse]:
    """ List Rag Provider Collections

     Lists all available vector database collections.

    Args:
        provider_id (UUID): ID of RAG provider configuration to use for authentication with the
            vector store.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchRagProviderCollectionsResponse]
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

) -> HTTPValidationError | SearchRagProviderCollectionsResponse | None:
    """ List Rag Provider Collections

     Lists all available vector database collections.

    Args:
        provider_id (UUID): ID of RAG provider configuration to use for authentication with the
            vector store.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchRagProviderCollectionsResponse
     """


    return sync_detailed(
        provider_id=provider_id,
client=client,

    ).parsed

async def asyncio_detailed(
    provider_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | SearchRagProviderCollectionsResponse]:
    """ List Rag Provider Collections

     Lists all available vector database collections.

    Args:
        provider_id (UUID): ID of RAG provider configuration to use for authentication with the
            vector store.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchRagProviderCollectionsResponse]
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

) -> HTTPValidationError | SearchRagProviderCollectionsResponse | None:
    """ List Rag Provider Collections

     Lists all available vector database collections.

    Args:
        provider_id (UUID): ID of RAG provider configuration to use for authentication with the
            vector store.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchRagProviderCollectionsResponse
     """


    return (await asyncio_detailed(
        provider_id=provider_id,
client=client,

    )).parsed
