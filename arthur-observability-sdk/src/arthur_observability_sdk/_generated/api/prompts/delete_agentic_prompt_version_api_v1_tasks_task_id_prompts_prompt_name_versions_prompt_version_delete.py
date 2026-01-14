from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    prompt_name: str,
    prompt_version: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}".format(task_id=quote(str(task_id), safe=""),prompt_name=quote(str(prompt_name), safe=""),prompt_version=quote(str(prompt_version), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | HTTPValidationError | None:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: UUID,
    prompt_name: str,
    prompt_version: str,
    *,
    client: AuthenticatedClient,

) -> Response[Any | HTTPValidationError]:
    """ Delete an agentic prompt version

     Deletes a specific version of an agentic prompt

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to delete.
        prompt_version (str): The version of the prompt to delete. Can be 'latest', a version
            number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a
            tag.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
prompt_name=prompt_name,
prompt_version=prompt_version,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    prompt_name: str,
    prompt_version: str,
    *,
    client: AuthenticatedClient,

) -> Any | HTTPValidationError | None:
    """ Delete an agentic prompt version

     Deletes a specific version of an agentic prompt

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to delete.
        prompt_version (str): The version of the prompt to delete. Can be 'latest', a version
            number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a
            tag.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
     """


    return sync_detailed(
        task_id=task_id,
prompt_name=prompt_name,
prompt_version=prompt_version,
client=client,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    prompt_name: str,
    prompt_version: str,
    *,
    client: AuthenticatedClient,

) -> Response[Any | HTTPValidationError]:
    """ Delete an agentic prompt version

     Deletes a specific version of an agentic prompt

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to delete.
        prompt_version (str): The version of the prompt to delete. Can be 'latest', a version
            number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a
            tag.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
prompt_name=prompt_name,
prompt_version=prompt_version,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    prompt_name: str,
    prompt_version: str,
    *,
    client: AuthenticatedClient,

) -> Any | HTTPValidationError | None:
    """ Delete an agentic prompt version

     Deletes a specific version of an agentic prompt

    Args:
        task_id (UUID):
        prompt_name (str): The name of the prompt to delete.
        prompt_version (str): The version of the prompt to delete. Can be 'latest', a version
            number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a
            tag.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
     """


    return (await asyncio_detailed(
        task_id=task_id,
prompt_name=prompt_name,
prompt_version=prompt_version,
client=client,

    )).parsed
