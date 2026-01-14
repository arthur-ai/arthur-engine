from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.rag_search_setting_configuration_version_response import RagSearchSettingConfigurationVersionResponse
from ...models.rag_search_setting_configuration_version_update_request import RagSearchSettingConfigurationVersionUpdateRequest
from typing import cast
from uuid import UUID



def _get_kwargs(
    setting_configuration_id: UUID,
    version_number: int,
    *,
    body: RagSearchSettingConfigurationVersionUpdateRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/v1/rag_search_settings/{setting_configuration_id}/versions/{version_number}".format(setting_configuration_id=quote(str(setting_configuration_id), safe=""),version_number=quote(str(version_number), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
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
    version_number: int,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationVersionUpdateRequest,

) -> Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]:
    """ Update Rag Search Settings Version

     Update a single RAG search setting configuration version metadata.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to update.
        version_number (int): Version number of the version to update.
        body (RagSearchSettingConfigurationVersionUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,
version_number=version_number,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    setting_configuration_id: UUID,
    version_number: int,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationVersionUpdateRequest,

) -> HTTPValidationError | RagSearchSettingConfigurationVersionResponse | None:
    """ Update Rag Search Settings Version

     Update a single RAG search setting configuration version metadata.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to update.
        version_number (int): Version number of the version to update.
        body (RagSearchSettingConfigurationVersionUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationVersionResponse
     """


    return sync_detailed(
        setting_configuration_id=setting_configuration_id,
version_number=version_number,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    setting_configuration_id: UUID,
    version_number: int,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationVersionUpdateRequest,

) -> Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]:
    """ Update Rag Search Settings Version

     Update a single RAG search setting configuration version metadata.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to update.
        version_number (int): Version number of the version to update.
        body (RagSearchSettingConfigurationVersionUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationVersionResponse]
     """


    kwargs = _get_kwargs(
        setting_configuration_id=setting_configuration_id,
version_number=version_number,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    setting_configuration_id: UUID,
    version_number: int,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationVersionUpdateRequest,

) -> HTTPValidationError | RagSearchSettingConfigurationVersionResponse | None:
    """ Update Rag Search Settings Version

     Update a single RAG search setting configuration version metadata.

    Args:
        setting_configuration_id (UUID): ID of the RAG search setting configuration to update.
        version_number (int): Version number of the version to update.
        body (RagSearchSettingConfigurationVersionUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationVersionResponse
     """


    return (await asyncio_detailed(
        setting_configuration_id=setting_configuration_id,
version_number=version_number,
client=client,
body=body,

    )).parsed
