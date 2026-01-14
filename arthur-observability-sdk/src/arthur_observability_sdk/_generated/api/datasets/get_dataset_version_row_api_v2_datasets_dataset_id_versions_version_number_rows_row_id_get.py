from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.dataset_version_row_response import DatasetVersionRowResponse
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    dataset_id: UUID,
    version_number: int,
    row_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/datasets/{dataset_id}/versions/{version_number}/rows/{row_id}".format(dataset_id=quote(str(dataset_id), safe=""),version_number=quote(str(version_number), safe=""),row_id=quote(str(row_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> DatasetVersionRowResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = DatasetVersionRowResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[DatasetVersionRowResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    dataset_id: UUID,
    version_number: int,
    row_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[DatasetVersionRowResponse | HTTPValidationError]:
    """ Get Dataset Version Row

     Fetch a specific row from a dataset version by row ID.

    Args:
        dataset_id (UUID): ID of the dataset.
        version_number (int): Version number of the dataset.
        row_id (UUID): ID of the row to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DatasetVersionRowResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        dataset_id=dataset_id,
version_number=version_number,
row_id=row_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    dataset_id: UUID,
    version_number: int,
    row_id: UUID,
    *,
    client: AuthenticatedClient,

) -> DatasetVersionRowResponse | HTTPValidationError | None:
    """ Get Dataset Version Row

     Fetch a specific row from a dataset version by row ID.

    Args:
        dataset_id (UUID): ID of the dataset.
        version_number (int): Version number of the dataset.
        row_id (UUID): ID of the row to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DatasetVersionRowResponse | HTTPValidationError
     """


    return sync_detailed(
        dataset_id=dataset_id,
version_number=version_number,
row_id=row_id,
client=client,

    ).parsed

async def asyncio_detailed(
    dataset_id: UUID,
    version_number: int,
    row_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[DatasetVersionRowResponse | HTTPValidationError]:
    """ Get Dataset Version Row

     Fetch a specific row from a dataset version by row ID.

    Args:
        dataset_id (UUID): ID of the dataset.
        version_number (int): Version number of the dataset.
        row_id (UUID): ID of the row to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DatasetVersionRowResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        dataset_id=dataset_id,
version_number=version_number,
row_id=row_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    dataset_id: UUID,
    version_number: int,
    row_id: UUID,
    *,
    client: AuthenticatedClient,

) -> DatasetVersionRowResponse | HTTPValidationError | None:
    """ Get Dataset Version Row

     Fetch a specific row from a dataset version by row ID.

    Args:
        dataset_id (UUID): ID of the dataset.
        version_number (int): Version number of the dataset.
        row_id (UUID): ID of the row to fetch.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DatasetVersionRowResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        dataset_id=dataset_id,
version_number=version_number,
row_id=row_id,
client=client,

    )).parsed
