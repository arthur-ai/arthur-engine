from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.model_provider import ModelProvider
from ...models.model_provider_model_list import ModelProviderModelList
from typing import cast



def _get_kwargs(
    provider: ModelProvider,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/model_providers/{provider}/available_models".format(provider=quote(str(provider), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ModelProviderModelList | None:
    if response.status_code == 200:
        response_200 = ModelProviderModelList.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ModelProviderModelList]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    provider: ModelProvider,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | ModelProviderModelList]:
    """ List the models available from a provider.

     Returns a list of the names of all available models for a provider.

    Args:
        provider (ModelProvider):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ModelProviderModelList]
     """


    kwargs = _get_kwargs(
        provider=provider,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    provider: ModelProvider,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | ModelProviderModelList | None:
    """ List the models available from a provider.

     Returns a list of the names of all available models for a provider.

    Args:
        provider (ModelProvider):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ModelProviderModelList
     """


    return sync_detailed(
        provider=provider,
client=client,

    ).parsed

async def asyncio_detailed(
    provider: ModelProvider,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | ModelProviderModelList]:
    """ List the models available from a provider.

     Returns a list of the names of all available models for a provider.

    Args:
        provider (ModelProvider):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ModelProviderModelList]
     """


    kwargs = _get_kwargs(
        provider=provider,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    provider: ModelProvider,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | ModelProviderModelList | None:
    """ List the models available from a provider.

     Returns a list of the names of all available models for a provider.

    Args:
        provider (ModelProvider):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ModelProviderModelList
     """


    return (await asyncio_detailed(
        provider=provider,
client=client,

    )).parsed
