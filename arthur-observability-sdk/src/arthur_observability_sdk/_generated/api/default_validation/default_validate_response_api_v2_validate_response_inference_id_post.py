from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.response_validation_request import ResponseValidationRequest
from ...models.validation_result import ValidationResult
from typing import cast
from uuid import UUID



def _get_kwargs(
    inference_id: UUID,
    *,
    body: ResponseValidationRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/validate_response/{inference_id}".format(inference_id=quote(str(inference_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ValidationResult | None:
    if response.status_code == 200:
        response_200 = ValidationResult.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ValidationResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    inference_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ResponseValidationRequest,

) -> Response[HTTPValidationError | ValidationResult]:
    """ Default Validate Response

     [Deprecated] Validate a non-task related generated response based on the configured default rules.
    Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide
    context if a Hallucination Rule is an enabled default rule.

    Args:
        inference_id (UUID):
        body (ResponseValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ValidationResult]
     """


    kwargs = _get_kwargs(
        inference_id=inference_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    inference_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ResponseValidationRequest,

) -> HTTPValidationError | ValidationResult | None:
    """ Default Validate Response

     [Deprecated] Validate a non-task related generated response based on the configured default rules.
    Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide
    context if a Hallucination Rule is an enabled default rule.

    Args:
        inference_id (UUID):
        body (ResponseValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ValidationResult
     """


    return sync_detailed(
        inference_id=inference_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    inference_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ResponseValidationRequest,

) -> Response[HTTPValidationError | ValidationResult]:
    """ Default Validate Response

     [Deprecated] Validate a non-task related generated response based on the configured default rules.
    Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide
    context if a Hallucination Rule is an enabled default rule.

    Args:
        inference_id (UUID):
        body (ResponseValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ValidationResult]
     """


    kwargs = _get_kwargs(
        inference_id=inference_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    inference_id: UUID,
    *,
    client: AuthenticatedClient,
    body: ResponseValidationRequest,

) -> HTTPValidationError | ValidationResult | None:
    """ Default Validate Response

     [Deprecated] Validate a non-task related generated response based on the configured default rules.
    Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide
    context if a Hallucination Rule is an enabled default rule.

    Args:
        inference_id (UUID):
        body (ResponseValidationRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ValidationResult
     """


    return (await asyncio_detailed(
        inference_id=inference_id,
client=client,
body=body,

    )).parsed
