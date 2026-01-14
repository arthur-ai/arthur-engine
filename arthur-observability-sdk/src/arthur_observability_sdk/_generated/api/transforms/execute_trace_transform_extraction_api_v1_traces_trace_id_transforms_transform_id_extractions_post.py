from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.transform_extraction_response_list import TransformExtractionResponseList
from typing import cast
from uuid import UUID



def _get_kwargs(
    trace_id: str,
    transform_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/traces/{trace_id}/transforms/{transform_id}/extractions".format(trace_id=quote(str(trace_id), safe=""),transform_id=quote(str(transform_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | TransformExtractionResponseList | None:
    if response.status_code == 200:
        response_200 = TransformExtractionResponseList.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | TransformExtractionResponseList]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    trace_id: str,
    transform_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | TransformExtractionResponseList]:
    """ Execute Trace Transform Extraction

     Execute a transform against a trace to extract variables.

    Args:
        trace_id (str): ID of the trace to execute the transform against.
        transform_id (UUID): ID of the transform to execute.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TransformExtractionResponseList]
     """


    kwargs = _get_kwargs(
        trace_id=trace_id,
transform_id=transform_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    trace_id: str,
    transform_id: UUID,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | TransformExtractionResponseList | None:
    """ Execute Trace Transform Extraction

     Execute a transform against a trace to extract variables.

    Args:
        trace_id (str): ID of the trace to execute the transform against.
        transform_id (UUID): ID of the transform to execute.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TransformExtractionResponseList
     """


    return sync_detailed(
        trace_id=trace_id,
transform_id=transform_id,
client=client,

    ).parsed

async def asyncio_detailed(
    trace_id: str,
    transform_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[HTTPValidationError | TransformExtractionResponseList]:
    """ Execute Trace Transform Extraction

     Execute a transform against a trace to extract variables.

    Args:
        trace_id (str): ID of the trace to execute the transform against.
        transform_id (UUID): ID of the transform to execute.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TransformExtractionResponseList]
     """


    kwargs = _get_kwargs(
        trace_id=trace_id,
transform_id=transform_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    trace_id: str,
    transform_id: UUID,
    *,
    client: AuthenticatedClient,

) -> HTTPValidationError | TransformExtractionResponseList | None:
    """ Execute Trace Transform Extraction

     Execute a transform against a trace to extract variables.

    Args:
        trace_id (str): ID of the trace to execute the transform against.
        transform_id (UUID): ID of the transform to execute.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TransformExtractionResponseList
     """


    return (await asyncio_detailed(
        trace_id=trace_id,
transform_id=transform_id,
client=client,

    )).parsed
