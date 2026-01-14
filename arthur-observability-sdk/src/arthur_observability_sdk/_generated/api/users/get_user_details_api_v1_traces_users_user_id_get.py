from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.trace_user_metadata_response import TraceUserMetadataResponse
from typing import cast



def _get_kwargs(
    user_id: str,
    *,
    task_ids: list[str],

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_task_ids = task_ids


    params["task_ids"] = json_task_ids


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/traces/users/{user_id}".format(user_id=quote(str(user_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | TraceUserMetadataResponse | None:
    if response.status_code == 200:
        response_200 = TraceUserMetadataResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | TraceUserMetadataResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    user_id: str,
    *,
    client: AuthenticatedClient,
    task_ids: list[str],

) -> Response[HTTPValidationError | TraceUserMetadataResponse]:
    """ Get User Details

     Get detailed information for a single user including session and trace metadata.

    Args:
        user_id (str):
        task_ids (list[str]): Task IDs to filter on. At least one is required.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TraceUserMetadataResponse]
     """


    kwargs = _get_kwargs(
        user_id=user_id,
task_ids=task_ids,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    user_id: str,
    *,
    client: AuthenticatedClient,
    task_ids: list[str],

) -> HTTPValidationError | TraceUserMetadataResponse | None:
    """ Get User Details

     Get detailed information for a single user including session and trace metadata.

    Args:
        user_id (str):
        task_ids (list[str]): Task IDs to filter on. At least one is required.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TraceUserMetadataResponse
     """


    return sync_detailed(
        user_id=user_id,
client=client,
task_ids=task_ids,

    ).parsed

async def asyncio_detailed(
    user_id: str,
    *,
    client: AuthenticatedClient,
    task_ids: list[str],

) -> Response[HTTPValidationError | TraceUserMetadataResponse]:
    """ Get User Details

     Get detailed information for a single user including session and trace metadata.

    Args:
        user_id (str):
        task_ids (list[str]): Task IDs to filter on. At least one is required.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TraceUserMetadataResponse]
     """


    kwargs = _get_kwargs(
        user_id=user_id,
task_ids=task_ids,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    user_id: str,
    *,
    client: AuthenticatedClient,
    task_ids: list[str],

) -> HTTPValidationError | TraceUserMetadataResponse | None:
    """ Get User Details

     Get detailed information for a single user including session and trace metadata.

    Args:
        user_id (str):
        task_ids (list[str]): Task IDs to filter on. At least one is required.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TraceUserMetadataResponse
     """


    return (await asyncio_detailed(
        user_id=user_id,
client=client,
task_ids=task_ids,

    )).parsed
