from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.rag_config_result_list_response import RagConfigResultListResponse
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    experiment_id: str,
    rag_config_key: str,
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
        "url": "/api/v1/rag_experiments/{experiment_id}/rag_configs/{rag_config_key}/results".format(experiment_id=quote(str(experiment_id), safe=""),rag_config_key=quote(str(rag_config_key), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | RagConfigResultListResponse | None:
    if response.status_code == 200:
        response_200 = RagConfigResultListResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | RagConfigResultListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    experiment_id: str,
    rag_config_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | RagConfigResultListResponse]:
    """ Get RAG config results

     Get paginated list of results for a specific RAG configuration within an experiment (supports both
    saved and unsaved configs)

    Args:
        experiment_id (str): The ID of the experiment
        rag_config_key (str): The RAG config key (format: 'saved:setting_config_id:version' or
            'unsaved:uuid'). URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagConfigResultListResponse]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,
rag_config_key=rag_config_key,
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
    rag_config_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | RagConfigResultListResponse | None:
    """ Get RAG config results

     Get paginated list of results for a specific RAG configuration within an experiment (supports both
    saved and unsaved configs)

    Args:
        experiment_id (str): The ID of the experiment
        rag_config_key (str): The RAG config key (format: 'saved:setting_config_id:version' or
            'unsaved:uuid'). URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagConfigResultListResponse
     """


    return sync_detailed(
        experiment_id=experiment_id,
rag_config_key=rag_config_key,
client=client,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    experiment_id: str,
    rag_config_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | RagConfigResultListResponse]:
    """ Get RAG config results

     Get paginated list of results for a specific RAG configuration within an experiment (supports both
    saved and unsaved configs)

    Args:
        experiment_id (str): The ID of the experiment
        rag_config_key (str): The RAG config key (format: 'saved:setting_config_id:version' or
            'unsaved:uuid'). URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RagConfigResultListResponse]
     """


    kwargs = _get_kwargs(
        experiment_id=experiment_id,
rag_config_key=rag_config_key,
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
    rag_config_key: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | RagConfigResultListResponse | None:
    """ Get RAG config results

     Get paginated list of results for a specific RAG configuration within an experiment (supports both
    saved and unsaved configs)

    Args:
        experiment_id (str): The ID of the experiment
        rag_config_key (str): The RAG config key (format: 'saved:setting_config_id:version' or
            'unsaved:uuid'). URL-encode colons as %3A
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RagConfigResultListResponse
     """


    return (await asyncio_detailed(
        experiment_id=experiment_id,
rag_config_key=rag_config_key,
client=client,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
