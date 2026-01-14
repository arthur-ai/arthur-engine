from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.continuous_eval_rerun_response import ContinuousEvalRerunResponse
from ...models.http_validation_error import HTTPValidationError
from typing import cast
from uuid import UUID



def _get_kwargs(
    run_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/continuous_evals/results/{run_id}/rerun".format(run_id=quote(str(run_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ContinuousEvalRerunResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ContinuousEvalRerunResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ContinuousEvalRerunResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    run_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[ContinuousEvalRerunResponse | HTTPValidationError]:
    """ Rerun a failed continuous eval

     Rerun a failed continuous eval

    Args:
        run_id (UUID): The id of the continuous eval run to rerun.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContinuousEvalRerunResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        run_id=run_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    run_id: UUID,
    *,
    client: AuthenticatedClient,

) -> ContinuousEvalRerunResponse | HTTPValidationError | None:
    """ Rerun a failed continuous eval

     Rerun a failed continuous eval

    Args:
        run_id (UUID): The id of the continuous eval run to rerun.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContinuousEvalRerunResponse | HTTPValidationError
     """


    return sync_detailed(
        run_id=run_id,
client=client,

    ).parsed

async def asyncio_detailed(
    run_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[ContinuousEvalRerunResponse | HTTPValidationError]:
    """ Rerun a failed continuous eval

     Rerun a failed continuous eval

    Args:
        run_id (UUID): The id of the continuous eval run to rerun.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ContinuousEvalRerunResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        run_id=run_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    run_id: UUID,
    *,
    client: AuthenticatedClient,

) -> ContinuousEvalRerunResponse | HTTPValidationError | None:
    """ Rerun a failed continuous eval

     Rerun a failed continuous eval

    Args:
        run_id (UUID): The id of the continuous eval run to rerun.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ContinuousEvalRerunResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        run_id=run_id,
client=client,

    )).parsed
