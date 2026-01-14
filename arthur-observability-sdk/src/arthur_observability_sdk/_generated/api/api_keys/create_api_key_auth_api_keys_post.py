from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.api_key_response import ApiKeyResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.new_api_key_request import NewApiKeyRequest
from typing import cast



def _get_kwargs(
    *,
    body: NewApiKeyRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/auth/api_keys/",
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ApiKeyResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ApiKeyResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ApiKeyResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: NewApiKeyRequest,

) -> Response[ApiKeyResponse | HTTPValidationError]:
    """ Create Api Key

     Generates a new API key. Up to 1000 active keys can exist at the same time by default. Contact your
    system administrator if you need more. Allowed roles are: DEFAULT-RULE-ADMIN, TASK-ADMIN,
    VALIDATION-USER, ORG-AUDITOR, ORG-ADMIN.

    Args:
        body (NewApiKeyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiKeyResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    body: NewApiKeyRequest,

) -> ApiKeyResponse | HTTPValidationError | None:
    """ Create Api Key

     Generates a new API key. Up to 1000 active keys can exist at the same time by default. Contact your
    system administrator if you need more. Allowed roles are: DEFAULT-RULE-ADMIN, TASK-ADMIN,
    VALIDATION-USER, ORG-AUDITOR, ORG-ADMIN.

    Args:
        body (NewApiKeyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiKeyResponse | HTTPValidationError
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: NewApiKeyRequest,

) -> Response[ApiKeyResponse | HTTPValidationError]:
    """ Create Api Key

     Generates a new API key. Up to 1000 active keys can exist at the same time by default. Contact your
    system administrator if you need more. Allowed roles are: DEFAULT-RULE-ADMIN, TASK-ADMIN,
    VALIDATION-USER, ORG-AUDITOR, ORG-ADMIN.

    Args:
        body (NewApiKeyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiKeyResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    body: NewApiKeyRequest,

) -> ApiKeyResponse | HTTPValidationError | None:
    """ Create Api Key

     Generates a new API key. Up to 1000 active keys can exist at the same time by default. Contact your
    system administrator if you need more. Allowed roles are: DEFAULT-RULE-ADMIN, TASK-ADMIN,
    VALIDATION-USER, ORG-AUDITOR, ORG-ADMIN.

    Args:
        body (NewApiKeyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiKeyResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
