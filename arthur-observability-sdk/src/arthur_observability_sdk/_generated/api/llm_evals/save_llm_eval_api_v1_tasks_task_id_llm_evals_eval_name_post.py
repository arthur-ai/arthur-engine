from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.create_eval_request import CreateEvalRequest
from ...models.http_validation_error import HTTPValidationError
from ...models.llm_eval import LLMEval
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    eval_name: str,
    *,
    body: CreateEvalRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks/{task_id}/llm_evals/{eval_name}".format(task_id=quote(str(task_id), safe=""),eval_name=quote(str(eval_name), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | LLMEval | None:
    if response.status_code == 200:
        response_200 = LLMEval.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | LLMEval]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateEvalRequest,

) -> Response[HTTPValidationError | LLMEval]:
    """ Save an llm eval

     Save an llm eval to the database

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to save.
        body (CreateEvalRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LLMEval]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
eval_name=eval_name,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateEvalRequest,

) -> HTTPValidationError | LLMEval | None:
    """ Save an llm eval

     Save an llm eval to the database

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to save.
        body (CreateEvalRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LLMEval
     """


    return sync_detailed(
        task_id=task_id,
eval_name=eval_name,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateEvalRequest,

) -> Response[HTTPValidationError | LLMEval]:
    """ Save an llm eval

     Save an llm eval to the database

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to save.
        body (CreateEvalRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LLMEval]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
eval_name=eval_name,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    body: CreateEvalRequest,

) -> HTTPValidationError | LLMEval | None:
    """ Save an llm eval

     Save an llm eval to the database

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to save.
        body (CreateEvalRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LLMEval
     """


    return (await asyncio_detailed(
        task_id=task_id,
eval_name=eval_name,
client=client,
body=body,

    )).parsed
