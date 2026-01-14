from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.continuous_eval_response import ContinuousEvalResponse
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    eval_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/continuous_evals/{eval_id}".format(eval_id=quote(str(eval_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ContinuousEvalResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ContinuousEvalResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ContinuousEvalResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    eval_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[ContinuousEvalResponse | HTTPValidationError]:
    """ Get a continuous eval by id

     Get a continuous eval by id

    Args:
        eval_id (UUID): The id of the continuous eval to retrieve.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContinuousEvalResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        eval_id=eval_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    eval_id: UUID,
    *,
    client: AuthenticatedClient,

) -> ContinuousEvalResponse | HTTPValidationError | None:
    """ Get a continuous eval by id

     Get a continuous eval by id

    Args:
        eval_id (UUID): The id of the continuous eval to retrieve.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContinuousEvalResponse | HTTPValidationError
     """


    return sync_detailed(
        eval_id=eval_id,
client=client,

    ).parsed

async def asyncio_detailed(
    eval_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[ContinuousEvalResponse | HTTPValidationError]:
    """ Get a continuous eval by id

     Get a continuous eval by id

    Args:
        eval_id (UUID): The id of the continuous eval to retrieve.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContinuousEvalResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        eval_id=eval_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    eval_id: UUID,
    *,
    client: AuthenticatedClient,

) -> ContinuousEvalResponse | HTTPValidationError | None:
    """ Get a continuous eval by id

     Get a continuous eval by id

    Args:
        eval_id (UUID): The id of the continuous eval to retrieve.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContinuousEvalResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        eval_id=eval_id,
client=client,

    )).parsed
