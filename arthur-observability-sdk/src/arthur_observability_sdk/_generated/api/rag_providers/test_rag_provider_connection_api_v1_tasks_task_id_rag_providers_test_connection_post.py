from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.connection_check_result import ConnectionCheckResult
from ...models.http_validation_error import HTTPValidationError
from ...models.rag_provider_test_configuration_request import RagProviderTestConfigurationRequest
from typing import cast



def _get_kwargs(
    task_id: str,
    *,
    body: RagProviderTestConfigurationRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks/{task_id}/rag_providers/test_connection".format(task_id=quote(str(task_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ConnectionCheckResult | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ConnectionCheckResult.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ConnectionCheckResult | HTTPValidationError]:
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
    body: RagProviderTestConfigurationRequest,

) -> Response[ConnectionCheckResult | HTTPValidationError]:
    """ Test Rag Provider Connection

     Test a new RAG provider connection configuration.

    Args:
        task_id (str): ID of the task to test the new provider connection for. Should be formatted
            as a UUID.
        body (RagProviderTestConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConnectionCheckResult | HTTPValidationError]
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
    body: RagProviderTestConfigurationRequest,

) -> ConnectionCheckResult | HTTPValidationError | None:
    """ Test Rag Provider Connection

     Test a new RAG provider connection configuration.

    Args:
        task_id (str): ID of the task to test the new provider connection for. Should be formatted
            as a UUID.
        body (RagProviderTestConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConnectionCheckResult | HTTPValidationError
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
    body: RagProviderTestConfigurationRequest,

) -> Response[ConnectionCheckResult | HTTPValidationError]:
    """ Test Rag Provider Connection

     Test a new RAG provider connection configuration.

    Args:
        task_id (str): ID of the task to test the new provider connection for. Should be formatted
            as a UUID.
        body (RagProviderTestConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConnectionCheckResult | HTTPValidationError]
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
    body: RagProviderTestConfigurationRequest,

) -> ConnectionCheckResult | HTTPValidationError | None:
    """ Test Rag Provider Connection

     Test a new RAG provider connection configuration.

    Args:
        task_id (str): ID of the task to test the new provider connection for. Should be formatted
            as a UUID.
        body (RagProviderTestConfigurationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConnectionCheckResult | HTTPValidationError
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
body=body,

    )).parsed
