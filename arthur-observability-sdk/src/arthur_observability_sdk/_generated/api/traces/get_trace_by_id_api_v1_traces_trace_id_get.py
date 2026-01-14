from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.trace_response import TraceResponse
from typing import cast



def _get_kwargs(
    trace_id: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/traces/{trace_id}".format(trace_id=quote(str(trace_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | TraceResponse | None:
    if response.status_code == 200:
        response_200 = TraceResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | TraceResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    trace_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | TraceResponse]:
    """ Get Single Trace

     Get complete trace tree with existing metrics (no computation). Returns full trace structure with
    spans.

    Args:
        trace_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TraceResponse]
     """


    kwargs = _get_kwargs(
        trace_id=trace_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    trace_id: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | TraceResponse | None:
    """ Get Single Trace

     Get complete trace tree with existing metrics (no computation). Returns full trace structure with
    spans.

    Args:
        trace_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TraceResponse
     """


    return sync_detailed(
        trace_id=trace_id,
client=client,

    ).parsed

async def asyncio_detailed(
    trace_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | TraceResponse]:
    """ Get Single Trace

     Get complete trace tree with existing metrics (no computation). Returns full trace structure with
    spans.

    Args:
        trace_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TraceResponse]
     """


    kwargs = _get_kwargs(
        trace_id=trace_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    trace_id: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | TraceResponse | None:
    """ Get Single Trace

     Get complete trace tree with existing metrics (no computation). Returns full trace structure with
    spans.

    Args:
        trace_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TraceResponse
     """


    return (await asyncio_detailed(
        trace_id=trace_id,
client=client,

    )).parsed
