from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.create_prompt_experiment_request import CreatePromptExperimentRequest
from ...models.http_validation_error import HTTPValidationError
from ...models.prompt_experiment_summary import PromptExperimentSummary
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    *,
    body: CreatePromptExperimentRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks/{task_id}/prompt_experiments".format(task_id=quote(str(task_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | PromptExperimentSummary | None:
    if response.status_code == 200:
        response_200 = PromptExperimentSummary.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | PromptExperimentSummary]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    body: CreatePromptExperimentRequest,

) -> Response[HTTPValidationError | PromptExperimentSummary]:
    """ Create and run a prompt experiment

     Create a new prompt experiment and initiate execution

    Args:
        task_id (UUID):
        body (CreatePromptExperimentRequest): Request to create a new prompt experiment

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptExperimentSummary]
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
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    body: CreatePromptExperimentRequest,

) -> HTTPValidationError | PromptExperimentSummary | None:
    """ Create and run a prompt experiment

     Create a new prompt experiment and initiate execution

    Args:
        task_id (UUID):
        body (CreatePromptExperimentRequest): Request to create a new prompt experiment

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptExperimentSummary
     """


    return sync_detailed(
        task_id=task_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    body: CreatePromptExperimentRequest,

) -> Response[HTTPValidationError | PromptExperimentSummary]:
    """ Create and run a prompt experiment

     Create a new prompt experiment and initiate execution

    Args:
        task_id (UUID):
        body (CreatePromptExperimentRequest): Request to create a new prompt experiment

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptExperimentSummary]
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
    task_id: UUID,
    *,
    client: AuthenticatedClient,
    body: CreatePromptExperimentRequest,

) -> HTTPValidationError | PromptExperimentSummary | None:
    """ Create and run a prompt experiment

     Create a new prompt experiment and initiate execution

    Args:
        task_id (UUID):
        body (CreatePromptExperimentRequest): Request to create a new prompt experiment

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptExperimentSummary
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
body=body,

    )).parsed
