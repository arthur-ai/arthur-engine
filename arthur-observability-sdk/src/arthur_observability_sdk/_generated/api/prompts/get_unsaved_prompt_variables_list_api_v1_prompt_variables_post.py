from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.unsaved_prompt_variables_list_response import UnsavedPromptVariablesListResponse
from ...models.unsaved_prompt_variables_request import UnsavedPromptVariablesRequest
from typing import cast



def _get_kwargs(
    *,
    body: UnsavedPromptVariablesRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/prompt_variables",
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | UnsavedPromptVariablesListResponse | None:
    if response.status_code == 200:
        response_200 = UnsavedPromptVariablesListResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | UnsavedPromptVariablesListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: UnsavedPromptVariablesRequest,

) -> Response[HTTPValidationError | UnsavedPromptVariablesListResponse]:
    """ Gets the list of variables needed from an unsaved prompt's messages

     Gets the list of variables needed from an unsaved prompt's messages

    Args:
        body (UnsavedPromptVariablesRequest): Request schema for getting the list of variables
            needed from an unsaved prompt's messages

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UnsavedPromptVariablesListResponse]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    body: UnsavedPromptVariablesRequest,

) -> HTTPValidationError | UnsavedPromptVariablesListResponse | None:
    """ Gets the list of variables needed from an unsaved prompt's messages

     Gets the list of variables needed from an unsaved prompt's messages

    Args:
        body (UnsavedPromptVariablesRequest): Request schema for getting the list of variables
            needed from an unsaved prompt's messages

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UnsavedPromptVariablesListResponse
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: UnsavedPromptVariablesRequest,

) -> Response[HTTPValidationError | UnsavedPromptVariablesListResponse]:
    """ Gets the list of variables needed from an unsaved prompt's messages

     Gets the list of variables needed from an unsaved prompt's messages

    Args:
        body (UnsavedPromptVariablesRequest): Request schema for getting the list of variables
            needed from an unsaved prompt's messages

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | UnsavedPromptVariablesListResponse]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    body: UnsavedPromptVariablesRequest,

) -> HTTPValidationError | UnsavedPromptVariablesListResponse | None:
    """ Gets the list of variables needed from an unsaved prompt's messages

     Gets the list of variables needed from an unsaved prompt's messages

    Args:
        body (UnsavedPromptVariablesRequest): Request schema for getting the list of variables
            needed from an unsaved prompt's messages

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | UnsavedPromptVariablesListResponse
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
