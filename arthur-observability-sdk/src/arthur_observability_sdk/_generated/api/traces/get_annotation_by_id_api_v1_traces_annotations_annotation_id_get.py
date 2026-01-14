from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.agentic_annotation_response import AgenticAnnotationResponse
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    annotation_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/traces/annotations/{annotation_id}".format(annotation_id=quote(str(annotation_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> AgenticAnnotationResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = AgenticAnnotationResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[AgenticAnnotationResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    annotation_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[AgenticAnnotationResponse | HTTPValidationError]:
    """ Get an annotation by id

     Get an annotation by id

    Args:
        annotation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AgenticAnnotationResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        annotation_id=annotation_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    annotation_id: UUID,
    *,
    client: AuthenticatedClient,

) -> AgenticAnnotationResponse | HTTPValidationError | None:
    """ Get an annotation by id

     Get an annotation by id

    Args:
        annotation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AgenticAnnotationResponse | HTTPValidationError
     """


    return sync_detailed(
        annotation_id=annotation_id,
client=client,

    ).parsed

async def asyncio_detailed(
    annotation_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[AgenticAnnotationResponse | HTTPValidationError]:
    """ Get an annotation by id

     Get an annotation by id

    Args:
        annotation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AgenticAnnotationResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        annotation_id=annotation_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    annotation_id: UUID,
    *,
    client: AuthenticatedClient,

) -> AgenticAnnotationResponse | HTTPValidationError | None:
    """ Get an annotation by id

     Get an annotation by id

    Args:
        annotation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AgenticAnnotationResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        annotation_id=annotation_id,
client=client,

    )).parsed
