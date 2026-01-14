from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.chat_document_context import ChatDocumentContext
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    inference_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/chat/context/{inference_id}".format(inference_id=quote(str(inference_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[ChatDocumentContext] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = ChatDocumentContext.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[ChatDocumentContext]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    inference_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[HTTPValidationError | list[ChatDocumentContext]]:
    """ Get Inference Document Context

     Get document context used for a past inference ID.

    Args:
        inference_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ChatDocumentContext]]
     """


    kwargs = _get_kwargs(
        inference_id=inference_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    inference_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> HTTPValidationError | list[ChatDocumentContext] | None:
    """ Get Inference Document Context

     Get document context used for a past inference ID.

    Args:
        inference_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ChatDocumentContext]
     """


    return sync_detailed(
        inference_id=inference_id,
client=client,

    ).parsed

async def asyncio_detailed(
    inference_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[HTTPValidationError | list[ChatDocumentContext]]:
    """ Get Inference Document Context

     Get document context used for a past inference ID.

    Args:
        inference_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ChatDocumentContext]]
     """


    kwargs = _get_kwargs(
        inference_id=inference_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    inference_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> HTTPValidationError | list[ChatDocumentContext] | None:
    """ Get Inference Document Context

     Get document context used for a past inference ID.

    Args:
        inference_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ChatDocumentContext]
     """


    return (await asyncio_detailed(
        inference_id=inference_id,
client=client,

    )).parsed
