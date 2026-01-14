from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.prompt_experiment_summary import PromptExperimentSummary
from typing import cast



def _get_kwargs(
    experiment_id: str,
    *,
    notebook_id: str,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["notebook_id"] = notebook_id


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/v1/prompt_experiments/{experiment_id}/notebook".format(experiment_id=quote(str(experiment_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | PromptExperimentSummary | None:
    if response.status_code == 200:
        response_200 = PromptExperimentSummary.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | PromptExperimentSummary]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    experiment_id: str,
    *,
    client: AuthenticatedClient,
    notebook_id: str,

) -> Response[HTTPValidationError | PromptExperimentSummary]:
    """ Attach notebook to experiment

     Attach a notebook to an existing experiment

    Args:
        experiment_id (str): ID of the experiment
        notebook_id (str): ID of the notebook to attach

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptExperimentSummary]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,
notebook_id=notebook_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    experiment_id: str,
    *,
    client: AuthenticatedClient,
    notebook_id: str,

) -> HTTPValidationError | PromptExperimentSummary | None:
    """ Attach notebook to experiment

     Attach a notebook to an existing experiment

    Args:
        experiment_id (str): ID of the experiment
        notebook_id (str): ID of the notebook to attach

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptExperimentSummary
     """


    return sync_detailed(
        experiment_id=experiment_id,
client=client,
notebook_id=notebook_id,

    ).parsed

async def asyncio_detailed(
    experiment_id: str,
    *,
    client: AuthenticatedClient,
    notebook_id: str,

) -> Response[HTTPValidationError | PromptExperimentSummary]:
    """ Attach notebook to experiment

     Attach a notebook to an existing experiment

    Args:
        experiment_id (str): ID of the experiment
        notebook_id (str): ID of the notebook to attach

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptExperimentSummary]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,
notebook_id=notebook_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    experiment_id: str,
    *,
    client: AuthenticatedClient,
    notebook_id: str,

) -> HTTPValidationError | PromptExperimentSummary | None:
    """ Attach notebook to experiment

     Attach a notebook to an existing experiment

    Args:
        experiment_id (str): ID of the experiment
        notebook_id (str): ID of the notebook to attach

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptExperimentSummary
     """


    return (await asyncio_detailed(
        experiment_id=experiment_id,
client=client,
notebook_id=notebook_id,

    )).parsed
