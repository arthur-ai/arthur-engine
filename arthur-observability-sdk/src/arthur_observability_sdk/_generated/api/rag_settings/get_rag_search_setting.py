from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.rag_search_setting_configuration_response import RagSearchSettingConfigurationResponse
from typing import cast
from uuid import UUID



def _get_kwargs(
    setting_configuration_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/rag_search_settings/{setting_configuration_id}".format(setting_configuration_id=quote(str(setting_configuration_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | RagSearchSettingConfigurationResponse | None:
    if response.status_code == 200:
        response_200 = RagSearchSettingConfigurationResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | RagSearchSettingConfigurationResponse]:
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

) -> Response[HTTPValidationError | RagSearchSettingConfigurationResponse]:
    """ Get Rag Search Setting

     Get a single RAG setting configuration.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    setting_configuration_id: UUID,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | RagSearchSettingConfigurationResponse | None:
    """ Get Rag Search Setting

     Get a single RAG setting configuration.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationResponse
     """


    return sync_detailed(
        setting_configuration_id=setting_configuration_id,
client=client,

    ).parsed

async def asyncio_detailed(
    setting_configuration_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | RagSearchSettingConfigurationResponse]:
    """ Get Rag Search Setting

     Get a single RAG setting configuration.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    setting_configuration_id: UUID,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | RagSearchSettingConfigurationResponse | None:
    """ Get Rag Search Setting

     Get a single RAG setting configuration.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationResponse
     """


    return (await asyncio_detailed(
        setting_configuration_id=setting_configuration_id,
client=client,

    )).parsed
