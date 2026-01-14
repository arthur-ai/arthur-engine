from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from typing import cast



def _get_kwargs(
    experiment_id: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/rag_experiments/{experiment_id}".format(experiment_id=quote(str(experiment_id), safe=""),),
    }


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
    experiment_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError]:
    """ Get RAG experiment details

     Get detailed information about a specific RAG experiment including summary results

    Args:
        experiment_id (str): The ID of the experiment to retrieve

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    experiment_id: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | None:
    """ Get RAG experiment details

     Get detailed information about a specific RAG experiment including summary results

    Args:
        experiment_id (str): The ID of the experiment to retrieve

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return sync_detailed(
        experiment_id=experiment_id,
client=client,

    ).parsed

async def asyncio_detailed(
    experiment_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError]:
    """ Get RAG experiment details

     Get detailed information about a specific RAG experiment including summary results

    Args:
        experiment_id (str): The ID of the experiment to retrieve

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    experiment_id: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | None:
    """ Get RAG experiment details

     Get detailed information about a specific RAG experiment including summary results

    Args:
        experiment_id (str): The ID of the experiment to retrieve

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return (await asyncio_detailed(
        experiment_id=experiment_id,
client=client,

    )).parsed
