from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.span_with_metrics_response import SpanWithMetricsResponse
from typing import cast



def _get_kwargs(
    span_id: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/traces/spans/{span_id}".format(span_id=quote(str(span_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | SpanWithMetricsResponse | None:
    if response.status_code == 200:
        response_200 = SpanWithMetricsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | SpanWithMetricsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    span_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | SpanWithMetricsResponse]:
    """ Get Single Span

     Get single span with existing metrics (no computation). Returns full span object with any existing
    metrics.

    Args:
        span_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SpanWithMetricsResponse]
     """


    kwargs = _get_kwargs(
        span_id=span_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    span_id: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | SpanWithMetricsResponse | None:
    """ Get Single Span

     Get single span with existing metrics (no computation). Returns full span object with any existing
    metrics.

    Args:
        span_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SpanWithMetricsResponse
     """


    return sync_detailed(
        span_id=span_id,
client=client,

    ).parsed

async def asyncio_detailed(
    span_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | SpanWithMetricsResponse]:
    """ Get Single Span

     Get single span with existing metrics (no computation). Returns full span object with any existing
    metrics.

    Args:
        span_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SpanWithMetricsResponse]
     """


    kwargs = _get_kwargs(
        span_id=span_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    span_id: str,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | SpanWithMetricsResponse | None:
    """ Get Single Span

     Get single span with existing metrics (no computation). Returns full span object with any existing
    metrics.

    Args:
        span_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SpanWithMetricsResponse
     """


    return (await asyncio_detailed(
        span_id=span_id,
client=client,

    )).parsed
