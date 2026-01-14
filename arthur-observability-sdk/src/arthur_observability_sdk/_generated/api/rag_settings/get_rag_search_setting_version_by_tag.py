from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.rag_search_setting_configuration_version_response import RagSearchSettingConfigurationVersionResponse
from typing import cast
from uuid import UUID



def _get_kwargs(
    setting_configuration_id: UUID,
    tag: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/rag_search_settings/{setting_configuration_id}/versions/tags/{tag}".format(setting_configuration_id=quote(str(setting_configuration_id), safe=""),tag=quote(str(tag), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | RagSearchSettingConfigurationVersionResponse | None:
    if response.status_code == 200:
        response_200 = RagSearchSettingConfigurationVersionResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    setting_configuration_id: UUID,
    tag: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]:
    """ Get Rag Search Setting Version By Tag

     Get a single RAG setting configuration version by tag.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.
        tag (str): Tag to fetch the version by.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,
tag=tag,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    setting_configuration_id: UUID,
    tag: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | RagSearchSettingConfigurationVersionResponse | None:
    """ Get Rag Search Setting Version By Tag

     Get a single RAG setting configuration version by tag.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.
        tag (str): Tag to fetch the version by.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationVersionResponse
     """


    return sync_detailed(
        setting_configuration_id=setting_configuration_id,
tag=tag,
client=client,

    ).parsed

async def asyncio_detailed(
    setting_configuration_id: UUID,
    tag: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]:
    """ Get Rag Search Setting Version By Tag

     Get a single RAG setting configuration version by tag.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.
        tag (str): Tag to fetch the version by.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,
tag=tag,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    setting_configuration_id: UUID,
    tag: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | RagSearchSettingConfigurationVersionResponse | None:
    """ Get Rag Search Setting Version By Tag

     Get a single RAG setting configuration version by tag.

    Args:
        setting_configuration_id (UUID): ID of RAG search setting configuration.
        tag (str): Tag to fetch the version by.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationVersionResponse
     """


    return (await asyncio_detailed(
        setting_configuration_id=setting_configuration_id,
tag=tag,
client=client,

    )).parsed
