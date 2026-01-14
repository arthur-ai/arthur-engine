from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.create_agentic_prompt_request import CreateAgenticPromptRequest
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    prompt_name: str,
    *,
    body: CreateAgenticPromptRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks/{task_id}/prompts/{prompt_name}".format(task_id=quote(str(task_id), safe=""),prompt_name=quote(str(prompt_name), safe=""),),
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
    task_id: UUID,
    prompt_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateAgenticPromptRequest,

) -> Response[HTTPValidationError]:
    """ Save an agentic prompt

     Save an agentic prompt to the database

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to save.
        body (CreateAgenticPromptRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
prompt_name=prompt_name,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    prompt_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateAgenticPromptRequest,

) -> HTTPValidationError | None:
    """ Save an agentic prompt

     Save an agentic prompt to the database

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to save.
        body (CreateAgenticPromptRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return sync_detailed(
        task_id=task_id,
prompt_name=prompt_name,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    prompt_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateAgenticPromptRequest,

) -> Response[HTTPValidationError]:
    """ Save an agentic prompt

     Save an agentic prompt to the database

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to save.
        body (CreateAgenticPromptRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
prompt_name=prompt_name,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    prompt_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateAgenticPromptRequest,

) -> HTTPValidationError | None:
    """ Save an agentic prompt

     Save an agentic prompt to the database

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to save.
        body (CreateAgenticPromptRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return (await asyncio_detailed(
        task_id=task_id,
prompt_name=prompt_name,
client=client,
body=body,

    )).parsed
