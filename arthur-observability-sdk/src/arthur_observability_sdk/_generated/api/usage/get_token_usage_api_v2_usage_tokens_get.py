from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.token_usage_response import TokenUsageResponse
from ...models.token_usage_scope import TokenUsageScope
from ...types import UNSET, Unset
from dateutil.parser import isoparse
from typing import cast
import datetime



def _get_kwargs(
    *,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    group_by: list[TokenUsageScope] | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_start_time: str | Unset = UNSET
    if not isinstance(start_time, Unset):
        json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time: str | Unset = UNSET
    if not isinstance(end_time, Unset):
        json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    json_group_by: list[str] | Unset = UNSET
    if not isinstance(group_by, Unset):
        json_group_by = []
        for group_by_item_data in group_by:
            group_by_item = group_by_item_data.value
            json_group_by.append(group_by_item)


    params["group_by"] = json_group_by


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/usage/tokens",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[TokenUsageResponse] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = TokenUsageResponse.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[TokenUsageResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    group_by: list[TokenUsageScope] | Unset = UNSET,

) -> Response[HTTPValidationError | list[TokenUsageResponse]]:
    """ Get Token Usage

     Get token usage.

    Args:
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
            Defaults to the beginning of the current day if not provided.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
            Defaults to the end of the current day if not provided.
        group_by (list[TokenUsageScope] | Unset): Entities to group token counts on.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[TokenUsageResponse]]
     """


    kwargs = _get_kwargs(
        start_time=start_time,
end_time=end_time,
group_by=group_by,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    group_by: list[TokenUsageScope] | Unset = UNSET,

) -> HTTPValidationError | list[TokenUsageResponse] | None:
    """ Get Token Usage

     Get token usage.

    Args:
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
            Defaults to the beginning of the current day if not provided.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
            Defaults to the end of the current day if not provided.
        group_by (list[TokenUsageScope] | Unset): Entities to group token counts on.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[TokenUsageResponse]
     """


    return sync_detailed(
        client=client,
start_time=start_time,
end_time=end_time,
group_by=group_by,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    group_by: list[TokenUsageScope] | Unset = UNSET,

) -> Response[HTTPValidationError | list[TokenUsageResponse]]:
    """ Get Token Usage

     Get token usage.

    Args:
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
            Defaults to the beginning of the current day if not provided.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
            Defaults to the end of the current day if not provided.
        group_by (list[TokenUsageScope] | Unset): Entities to group token counts on.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[TokenUsageResponse]]
     """


    kwargs = _get_kwargs(
        start_time=start_time,
end_time=end_time,
group_by=group_by,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    group_by: list[TokenUsageScope] | Unset = UNSET,

) -> HTTPValidationError | list[TokenUsageResponse] | None:
    """ Get Token Usage

     Get token usage.

    Args:
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
            Defaults to the beginning of the current day if not provided.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
            Defaults to the end of the current day if not provided.
        group_by (list[TokenUsageScope] | Unset): Entities to group token counts on.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[TokenUsageResponse]
     """


    return (await asyncio_detailed(
        client=client,
start_time=start_time,
end_time=end_time,
group_by=group_by,

    )).parsed
