from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.unsaved_prompt_rendering_request import UnsavedPromptRenderingRequest
from typing import cast



def _get_kwargs(
    *,
    body: UnsavedPromptRenderingRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/prompt_renders",
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | None:
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: UnsavedPromptRenderingRequest,

) -> Response[HTTPValidationError]:
    """ Render an unsaved prompt with variables

     Render an unsaved prompt by replacing template variables with provided values. Accepts messages
    directly in the request body instead of loading from database.

    Args:
        body (UnsavedPromptRenderingRequest): Request schema for rendering an unsaved agentic
            prompt with variables

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
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
    body: UnsavedPromptRenderingRequest,

) -> HTTPValidationError | None:
    """ Render an unsaved prompt with variables

     Render an unsaved prompt by replacing template variables with provided values. Accepts messages
    directly in the request body instead of loading from database.

    Args:
        body (UnsavedPromptRenderingRequest): Request schema for rendering an unsaved agentic
            prompt with variables

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: UnsavedPromptRenderingRequest,

) -> Response[HTTPValidationError]:
    """ Render an unsaved prompt with variables

     Render an unsaved prompt by replacing template variables with provided values. Accepts messages
    directly in the request body instead of loading from database.

    Args:
        body (UnsavedPromptRenderingRequest): Request schema for rendering an unsaved agentic
            prompt with variables

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
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
    body: UnsavedPromptRenderingRequest,

) -> HTTPValidationError | None:
    """ Render an unsaved prompt with variables

     Render an unsaved prompt by replacing template variables with provided values. Accepts messages
    directly in the request body instead of loading from database.

    Args:
        body (UnsavedPromptRenderingRequest): Request schema for rendering an unsaved agentic
            prompt with variables

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
