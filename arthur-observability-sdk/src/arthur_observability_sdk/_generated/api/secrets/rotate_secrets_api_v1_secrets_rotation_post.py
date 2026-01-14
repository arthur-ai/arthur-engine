from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors




def _get_kwargs(
    
) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/secrets/rotation",
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | None:
    if response.status_code == 204:
        return None

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,

) -> Response[Any]:
    """ Rotates secrets

     This endpoint re-encrypts all the secrets in the database. The procedure calling this endpoint is as
    follows:
    First: Deploy a new version of the service with GENAI_ENGINE_SECRET_STORE_KEY set to a value like
    'new-key::old-key'.
    Second: call this endpoint - all secrets will be re-encrypted with 'new-key'.
    Third: Deploy a new version of the service removing the old key from GENAI_ENGINE_SECRET_STORE_KEY,
    like 'new-key'.
    At this point all existing and new secrets will be managed by 'new-key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
     """


    kwargs = _get_kwargs(
        
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,

) -> Response[Any]:
    """ Rotates secrets

     This endpoint re-encrypts all the secrets in the database. The procedure calling this endpoint is as
    follows:
    First: Deploy a new version of the service with GENAI_ENGINE_SECRET_STORE_KEY set to a value like
    'new-key::old-key'.
    Second: call this endpoint - all secrets will be re-encrypted with 'new-key'.
    Third: Deploy a new version of the service removing the old key from GENAI_ENGINE_SECRET_STORE_KEY,
    like 'new-key'.
    At this point all existing and new secrets will be managed by 'new-key'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
     """


    kwargs = _get_kwargs(
        
    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

