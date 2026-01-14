from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.set_notebook_state_request import SetNotebookStateRequest
from typing import cast



def _get_kwargs(
    notebook_id: str,
    *,
    body: SetNotebookStateRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/v1/notebooks/{notebook_id}/state".format(notebook_id=quote(str(notebook_id), safe=""),),
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
    notebook_id: str,
    *,
    client: AuthenticatedClient,
    body: SetNotebookStateRequest,

) -> Response[HTTPValidationError]:
    """ Set notebook state

     Set the state (draft configuration) of a notebook

    Args:
        notebook_id (str): Notebook ID
        body (SetNotebookStateRequest): Request to set the notebook state

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
     """


    kwargs = _get_kwargs(
        notebook_id=notebook_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    notebook_id: str,
    *,
    client: AuthenticatedClient,
    body: SetNotebookStateRequest,

) -> HTTPValidationError | None:
    """ Set notebook state

     Set the state (draft configuration) of a notebook

    Args:
        notebook_id (str): Notebook ID
        body (SetNotebookStateRequest): Request to set the notebook state

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return sync_detailed(
        notebook_id=notebook_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    notebook_id: str,
    *,
    client: AuthenticatedClient,
    body: SetNotebookStateRequest,

) -> Response[HTTPValidationError]:
    """ Set notebook state

     Set the state (draft configuration) of a notebook

    Args:
        notebook_id (str): Notebook ID
        body (SetNotebookStateRequest): Request to set the notebook state

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError]
     """


    kwargs = _get_kwargs(
        notebook_id=notebook_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    notebook_id: str,
    *,
    client: AuthenticatedClient,
    body: SetNotebookStateRequest,

) -> HTTPValidationError | None:
    """ Set notebook state

     Set the state (draft configuration) of a notebook

    Args:
        notebook_id (str): Notebook ID
        body (SetNotebookStateRequest): Request to set the notebook state

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError
     """


    return (await asyncio_detailed(
        notebook_id=notebook_id,
client=client,
body=body,

    )).parsed
