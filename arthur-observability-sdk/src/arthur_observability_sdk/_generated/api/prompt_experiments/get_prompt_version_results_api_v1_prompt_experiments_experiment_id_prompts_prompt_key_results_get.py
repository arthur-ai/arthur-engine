from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.prompt_version_result_list_response import PromptVersionResultListResponse
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    experiment_id: str,
    prompt_key: str,
    *,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/prompt_experiments/{experiment_id}/prompts/{prompt_key}/results".format(experiment_id=quote(str(experiment_id), safe=""),prompt_key=quote(str(prompt_key), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | PromptVersionResultListResponse | None:
    if response.status_code == 200:
        response_200 = PromptVersionResultListResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | PromptVersionResultListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    experiment_id: str,
    prompt_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | PromptVersionResultListResponse]:
    """ Get prompt results

     Get paginated list of results for a specific prompt within an experiment (supports both saved and
    unsaved prompts)

    Args:
        experiment_id (str): The ID of the experiment
        prompt_key (str): The prompt key (format: 'saved:name:version' or 'unsaved:auto_name').
            URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptVersionResultListResponse]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,
prompt_key=prompt_key,
sort=sort,
page_size=page_size,
page=page,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    experiment_id: str,
    prompt_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | PromptVersionResultListResponse | None:
    """ Get prompt results

     Get paginated list of results for a specific prompt within an experiment (supports both saved and
    unsaved prompts)

    Args:
        experiment_id (str): The ID of the experiment
        prompt_key (str): The prompt key (format: 'saved:name:version' or 'unsaved:auto_name').
            URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptVersionResultListResponse
     """


    return sync_detailed(
        experiment_id=experiment_id,
prompt_key=prompt_key,
client=client,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    experiment_id: str,
    prompt_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | PromptVersionResultListResponse]:
    """ Get prompt results

     Get paginated list of results for a specific prompt within an experiment (supports both saved and
    unsaved prompts)

    Args:
        experiment_id (str): The ID of the experiment
        prompt_key (str): The prompt key (format: 'saved:name:version' or 'unsaved:auto_name').
            URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PromptVersionResultListResponse]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,
prompt_key=prompt_key,
sort=sort,
page_size=page_size,
page=page,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    experiment_id: str,
    prompt_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | PromptVersionResultListResponse | None:
    """ Get prompt results

     Get paginated list of results for a specific prompt within an experiment (supports both saved and
    unsaved prompts)

    Args:
        experiment_id (str): The ID of the experiment
        prompt_key (str): The prompt key (format: 'saved:name:version' or 'unsaved:auto_name').
            URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PromptVersionResultListResponse
     """


    return (await asyncio_detailed(
        experiment_id=experiment_id,
prompt_key=prompt_key,
client=client,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
