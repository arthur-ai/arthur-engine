from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.agentic_prompt_run_response import AgenticPromptRunResponse
from ...models.completion_request import CompletionRequest
from ...models.http_validation_error import HTTPValidationError
from typing import cast



def _get_kwargs(
    *,
    body: CompletionRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/completions",
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> AgenticPromptRunResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = AgenticPromptRunResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[AgenticPromptRunResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CompletionRequest,

) -> Response[AgenticPromptRunResponse | HTTPValidationError]:
    """ Run/Stream an unsaved agentic prompt

     Runs or streams an unsaved agentic prompt

    Args:
        body (CompletionRequest): Request schema for running an unsaved agentic prompt

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AgenticPromptRunResponse | HTTPValidationError]
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
    body: CompletionRequest,

) -> AgenticPromptRunResponse | HTTPValidationError | None:
    """ Run/Stream an unsaved agentic prompt

     Runs or streams an unsaved agentic prompt

    Args:
        body (CompletionRequest): Request schema for running an unsaved agentic prompt

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AgenticPromptRunResponse | HTTPValidationError
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CompletionRequest,

) -> Response[AgenticPromptRunResponse | HTTPValidationError]:
    """ Run/Stream an unsaved agentic prompt

     Runs or streams an unsaved agentic prompt

    Args:
        body (CompletionRequest): Request schema for running an unsaved agentic prompt

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AgenticPromptRunResponse | HTTPValidationError]
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
    body: CompletionRequest,

) -> AgenticPromptRunResponse | HTTPValidationError | None:
    """ Run/Stream an unsaved agentic prompt

     Runs or streams an unsaved agentic prompt

    Args:
        body (CompletionRequest): Request schema for running an unsaved agentic prompt

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AgenticPromptRunResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
