from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.dataset_response import DatasetResponse
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    dataset_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/datasets/{dataset_id}".format(dataset_id=quote(str(dataset_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> DatasetResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = DatasetResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[DatasetResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[DatasetResponse | HTTPValidationError]:
    """ Get Dataset

     Get a dataset.

    Args:
        dataset_id (UUID): ID of the dataset to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DatasetResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        dataset_id=dataset_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,

) -> DatasetResponse | HTTPValidationError | None:
    """ Get Dataset

     Get a dataset.

    Args:
        dataset_id (UUID): ID of the dataset to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DatasetResponse | HTTPValidationError
     """


    return sync_detailed(
        dataset_id=dataset_id,
client=client,

    ).parsed

async def asyncio_detailed(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[DatasetResponse | HTTPValidationError]:
    """ Get Dataset

     Get a dataset.

    Args:
        dataset_id (UUID): ID of the dataset to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DatasetResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        dataset_id=dataset_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    dataset_id: UUID,
    *,
    client: AuthenticatedClient,

) -> DatasetResponse | HTTPValidationError | None:
    """ Get Dataset

     Get a dataset.

    Args:
        dataset_id (UUID): ID of the dataset to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DatasetResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        dataset_id=dataset_id,
client=client,

    )).parsed
