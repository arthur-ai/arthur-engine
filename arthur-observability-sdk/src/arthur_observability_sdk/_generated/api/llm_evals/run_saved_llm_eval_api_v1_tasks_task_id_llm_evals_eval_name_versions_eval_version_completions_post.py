from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.base_completion_request import BaseCompletionRequest
from ...models.http_validation_error import HTTPValidationError
from ...models.llm_eval_run_response import LLMEvalRunResponse
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    eval_name: str,
    eval_version: str,
    *,
    body: BaseCompletionRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/completions".format(task_id=quote(str(task_id), safe=""),eval_name=quote(str(eval_name), safe=""),eval_version=quote(str(eval_version), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | LLMEvalRunResponse | None:
    if response.status_code == 200:
        response_200 = LLMEvalRunResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | LLMEvalRunResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: UUID,
    eval_name: str,
    eval_version: str,
    *,
    client: AuthenticatedClient,
    body: BaseCompletionRequest,

) -> Response[HTTPValidationError | LLMEvalRunResponse]:
    """ Run a saved llm eval

     Run a saved llm eval

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to run.
        eval_version (str): The version of the llm eval to run. Can be 'latest', a version number
            (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
        body (BaseCompletionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LLMEvalRunResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
eval_name=eval_name,
eval_version=eval_version,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    eval_name: str,
    eval_version: str,
    *,
    client: AuthenticatedClient,
    body: BaseCompletionRequest,

) -> HTTPValidationError | LLMEvalRunResponse | None:
    """ Run a saved llm eval

     Run a saved llm eval

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to run.
        eval_version (str): The version of the llm eval to run. Can be 'latest', a version number
            (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
        body (BaseCompletionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LLMEvalRunResponse
     """


    return sync_detailed(
        task_id=task_id,
eval_name=eval_name,
eval_version=eval_version,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    eval_name: str,
    eval_version: str,
    *,
    client: AuthenticatedClient,
    body: BaseCompletionRequest,

) -> Response[HTTPValidationError | LLMEvalRunResponse]:
    """ Run a saved llm eval

     Run a saved llm eval

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to run.
        eval_version (str): The version of the llm eval to run. Can be 'latest', a version number
            (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
        body (BaseCompletionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LLMEvalRunResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
eval_name=eval_name,
eval_version=eval_version,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    eval_name: str,
    eval_version: str,
    *,
    client: AuthenticatedClient,
    body: BaseCompletionRequest,

) -> HTTPValidationError | LLMEvalRunResponse | None:
    """ Run a saved llm eval

     Run a saved llm eval

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to run.
        eval_version (str): The version of the llm eval to run. Can be 'latest', a version number
            (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.
        body (BaseCompletionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LLMEvalRunResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
eval_name=eval_name,
eval_version=eval_version,
client=client,
body=body,

    )).parsed
