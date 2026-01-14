from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.task_response import TaskResponse
from ...models.update_metric_request import UpdateMetricRequest
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    metric_id: UUID,
    *,
    body: UpdateMetricRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/v2/tasks/{task_id}/metrics/{metric_id}".format(task_id=quote(str(task_id), safe=""),metric_id=quote(str(metric_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | TaskResponse | None:
    if response.status_code == 200:
        response_200 = TaskResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | TaskResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: UUID,
    metric_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateMetricRequest,

) -> Response[HTTPValidationError | TaskResponse]:
    """ Update Task Metric

     Update a task metric.

    Args:
        task_id (UUID):
        metric_id (UUID):
        body (UpdateMetricRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TaskResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
metric_id=metric_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    metric_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateMetricRequest,

) -> HTTPValidationError | TaskResponse | None:
    """ Update Task Metric

     Update a task metric.

    Args:
        task_id (UUID):
        metric_id (UUID):
        body (UpdateMetricRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TaskResponse
     """


    return sync_detailed(
        task_id=task_id,
metric_id=metric_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    metric_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateMetricRequest,

) -> Response[HTTPValidationError | TaskResponse]:
    """ Update Task Metric

     Update a task metric.

    Args:
        task_id (UUID):
        metric_id (UUID):
        body (UpdateMetricRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | TaskResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
metric_id=metric_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    metric_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateMetricRequest,

) -> HTTPValidationError | TaskResponse | None:
    """ Update Task Metric

     Update a task metric.

    Args:
        task_id (UUID):
        metric_id (UUID):
        body (UpdateMetricRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | TaskResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
metric_id=metric_id,
client=client,
body=body,

    )).parsed
