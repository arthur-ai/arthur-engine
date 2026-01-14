from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.rag_search_setting_configuration_request import RagSearchSettingConfigurationRequest
from ...models.rag_search_setting_configuration_response import RagSearchSettingConfigurationResponse
from typing import cast



def _get_kwargs(
    task_id: str,
    *,
    body: RagSearchSettingConfigurationRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks/{task_id}/rag_search_settings".format(task_id=quote(str(task_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
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
    task_id: str,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationRequest,

) -> Response[HTTPValidationError | RagSearchSettingConfigurationResponse]:
    """ Create Rag Search Settings

     Create a new RAG search settings configuration.

    Args:
        task_id (str): ID of the task to create the search settings configuration under.
        body (RagSearchSettingConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: str,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationRequest,

) -> HTTPValidationError | RagSearchSettingConfigurationResponse | None:
    """ Create Rag Search Settings

     Create a new RAG search settings configuration.

    Args:
        task_id (str): ID of the task to create the search settings configuration under.
        body (RagSearchSettingConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationResponse
     """


    return sync_detailed(
        task_id=task_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    task_id: str,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationRequest,

) -> Response[HTTPValidationError | RagSearchSettingConfigurationResponse]:
    """ Create Rag Search Settings

     Create a new RAG search settings configuration.

    Args:
        task_id (str): ID of the task to create the search settings configuration under.
        body (RagSearchSettingConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagSearchSettingConfigurationResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: str,
    *,
    client: AuthenticatedClient,
    body: RagSearchSettingConfigurationRequest,

) -> HTTPValidationError | RagSearchSettingConfigurationResponse | None:
    """ Create Rag Search Settings

     Create a new RAG search settings configuration.

    Args:
        task_id (str): ID of the task to create the search settings configuration under.
        body (RagSearchSettingConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagSearchSettingConfigurationResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
body=body,

    )).parsed
