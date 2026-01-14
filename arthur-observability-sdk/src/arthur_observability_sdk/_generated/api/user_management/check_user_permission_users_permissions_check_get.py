from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.user_permission_action import UserPermissionAction
from ...models.user_permission_resource import UserPermissionResource
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    action: UserPermissionAction | Unset = UNSET,
    resource: UserPermissionResource | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_action: str | Unset = UNSET
    if not isinstance(action, Unset):
        json_action = action.value

    params["action"] = json_action

    json_resource: str | Unset = UNSET
    if not isinstance(resource, Unset):
        json_resource = resource.value

    params["resource"] = json_resource


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/users/permissions/check",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = response.json()
        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    action: UserPermissionAction | Unset = UNSET,
    resource: UserPermissionResource | Unset = UNSET,

) -> Response[Any | HTTPValidationError]:
    """ Check User Permission

     Checks if the current user has the requested permission. Returns 200 status code for authorized or
    403 if not.

    Args:
        action (UserPermissionAction | Unset):
        resource (UserPermissionResource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        action=action,
resource=resource,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    action: UserPermissionAction | Unset = UNSET,
    resource: UserPermissionResource | Unset = UNSET,

) -> Any | HTTPValidationError | None:
    """ Check User Permission

     Checks if the current user has the requested permission. Returns 200 status code for authorized or
    403 if not.

    Args:
        action (UserPermissionAction | Unset):
        resource (UserPermissionResource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
     """


    return sync_detailed(
        client=client,
action=action,
resource=resource,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    action: UserPermissionAction | Unset = UNSET,
    resource: UserPermissionResource | Unset = UNSET,

) -> Response[Any | HTTPValidationError]:
    """ Check User Permission

     Checks if the current user has the requested permission. Returns 200 status code for authorized or
    403 if not.

    Args:
        action (UserPermissionAction | Unset):
        resource (UserPermissionResource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        action=action,
resource=resource,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    action: UserPermissionAction | Unset = UNSET,
    resource: UserPermissionResource | Unset = UNSET,

) -> Any | HTTPValidationError | None:
    """ Check User Permission

     Checks if the current user has the requested permission. Returns 200 status code for authorized or
    403 if not.

    Args:
        action (UserPermissionAction | Unset):
        resource (UserPermissionResource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
action=action,
resource=resource,

    )).parsed
