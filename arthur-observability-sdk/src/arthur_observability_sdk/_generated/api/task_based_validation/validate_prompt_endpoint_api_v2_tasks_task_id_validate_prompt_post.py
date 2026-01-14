from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_error import HTTPError
from ...models.http_validation_error import HTTPValidationError
from ...models.prompt_validation_request import PromptValidationRequest
from ...models.validation_result import ValidationResult
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    *,
    body: PromptValidationRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/tasks/{task_id}/validate_prompt".format(task_id=quote(str(task_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPError | HTTPValidationError | ValidationResult | None:
    if response.status_code == 200:
        response_200 = ValidationResult.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = HTTPError.from_dict(response.json())



        return response_400

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPError | HTTPValidationError | ValidationResult]:
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
    body: PromptValidationRequest,

) -> Response[HTTPError | HTTPValidationError | ValidationResult]:
    """ Validate Prompt Endpoint

     Validate a prompt based on the configured rules for this task. Note: Rules related to specific tasks
    are cached for 60 seconds.

    Args:
        task_id (UUID):
        body (PromptValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPError | HTTPValidationError | ValidationResult]
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
    body: PromptValidationRequest,

) -> HTTPError | HTTPValidationError | ValidationResult | None:
    """ Validate Prompt Endpoint

     Validate a prompt based on the configured rules for this task. Note: Rules related to specific tasks
    are cached for 60 seconds.

    Args:
        task_id (UUID):
        body (PromptValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPError | HTTPValidationError | ValidationResult
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
    body: PromptValidationRequest,

) -> Response[HTTPError | HTTPValidationError | ValidationResult]:
    """ Validate Prompt Endpoint

     Validate a prompt based on the configured rules for this task. Note: Rules related to specific tasks
    are cached for 60 seconds.

    Args:
        task_id (UUID):
        body (PromptValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPError | HTTPValidationError | ValidationResult]
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
    body: PromptValidationRequest,

) -> HTTPError | HTTPValidationError | ValidationResult | None:
    """ Validate Prompt Endpoint

     Validate a prompt based on the configured rules for this task. Note: Rules related to specific tasks
    are cached for 60 seconds.

    Args:
        task_id (UUID):
        body (PromptValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPError | HTTPValidationError | ValidationResult
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
body=body,

    )).parsed
