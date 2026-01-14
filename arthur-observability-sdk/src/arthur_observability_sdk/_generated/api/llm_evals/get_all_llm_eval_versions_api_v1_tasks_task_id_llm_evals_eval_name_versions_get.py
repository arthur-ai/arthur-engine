from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.llm_evals_version_list_response import LLMEvalsVersionListResponse
from ...models.pagination_sort_method import PaginationSortMethod
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    task_id: UUID,
    eval_name: str,
    *,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    model_provider: None | str | Unset = UNSET,
    model_name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,
    exclude_deleted: bool | Unset = False,
    min_version: int | None | Unset = UNSET,
    max_version: int | None | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page

    json_model_provider: None | str | Unset
    if isinstance(model_provider, Unset):
        json_model_provider = UNSET
    else:
        json_model_provider = model_provider
    params["model_provider"] = json_model_provider

    json_model_name: None | str | Unset
    if isinstance(model_name, Unset):
        json_model_name = UNSET
    else:
        json_model_name = model_name
    params["model_name"] = json_model_name

    json_created_after: None | str | Unset
    if isinstance(created_after, Unset):
        json_created_after = UNSET
    else:
        json_created_after = created_after
    params["created_after"] = json_created_after

    json_created_before: None | str | Unset
    if isinstance(created_before, Unset):
        json_created_before = UNSET
    else:
        json_created_before = created_before
    params["created_before"] = json_created_before

    params["exclude_deleted"] = exclude_deleted

    json_min_version: int | None | Unset
    if isinstance(min_version, Unset):
        json_min_version = UNSET
    else:
        json_min_version = min_version
    params["min_version"] = json_min_version

    json_max_version: int | None | Unset
    if isinstance(max_version, Unset):
        json_max_version = UNSET
    else:
        json_max_version = max_version
    params["max_version"] = json_max_version


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions".format(task_id=quote(str(task_id), safe=""),eval_name=quote(str(eval_name), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | LLMEvalsVersionListResponse | None:
    if response.status_code == 200:
        response_200 = LLMEvalsVersionListResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | LLMEvalsVersionListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    model_provider: None | str | Unset = UNSET,
    model_name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,
    exclude_deleted: bool | Unset = False,
    min_version: int | None | Unset = UNSET,
    max_version: int | None | Unset = UNSET,

) -> Response[HTTPValidationError | LLMEvalsVersionListResponse]:
    """ List all versions of an llm eval

     List all versions of an llm eval with optional filtering.

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to retrieve.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        model_provider (None | str | Unset): Filter by model provider (e.g., 'openai',
            'anthropic', 'azure').
        model_name (None | str | Unset): Filter by model name (e.g., 'gpt-4',
            'claude-3-5-sonnet').
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        exclude_deleted (bool | Unset): Whether to exclude deleted prompt versions from the
            results. Default is False. Default: False.
        min_version (int | None | Unset): Minimum version number to filter on (inclusive).
        max_version (int | None | Unset): Maximum version number to filter on (inclusive).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LLMEvalsVersionListResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
eval_name=eval_name,
sort=sort,
page_size=page_size,
page=page,
model_provider=model_provider,
model_name=model_name,
created_after=created_after,
created_before=created_before,
exclude_deleted=exclude_deleted,
min_version=min_version,
max_version=max_version,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    model_provider: None | str | Unset = UNSET,
    model_name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,
    exclude_deleted: bool | Unset = False,
    min_version: int | None | Unset = UNSET,
    max_version: int | None | Unset = UNSET,

) -> HTTPValidationError | LLMEvalsVersionListResponse | None:
    """ List all versions of an llm eval

     List all versions of an llm eval with optional filtering.

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to retrieve.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        model_provider (None | str | Unset): Filter by model provider (e.g., 'openai',
            'anthropic', 'azure').
        model_name (None | str | Unset): Filter by model name (e.g., 'gpt-4',
            'claude-3-5-sonnet').
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        exclude_deleted (bool | Unset): Whether to exclude deleted prompt versions from the
            results. Default is False. Default: False.
        min_version (int | None | Unset): Minimum version number to filter on (inclusive).
        max_version (int | None | Unset): Maximum version number to filter on (inclusive).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LLMEvalsVersionListResponse
     """


    return sync_detailed(
        task_id=task_id,
eval_name=eval_name,
client=client,
sort=sort,
page_size=page_size,
page=page,
model_provider=model_provider,
model_name=model_name,
created_after=created_after,
created_before=created_before,
exclude_deleted=exclude_deleted,
min_version=min_version,
max_version=max_version,

    ).parsed

async def asyncio_detailed(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    model_provider: None | str | Unset = UNSET,
    model_name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,
    exclude_deleted: bool | Unset = False,
    min_version: int | None | Unset = UNSET,
    max_version: int | None | Unset = UNSET,

) -> Response[HTTPValidationError | LLMEvalsVersionListResponse]:
    """ List all versions of an llm eval

     List all versions of an llm eval with optional filtering.

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to retrieve.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        model_provider (None | str | Unset): Filter by model provider (e.g., 'openai',
            'anthropic', 'azure').
        model_name (None | str | Unset): Filter by model name (e.g., 'gpt-4',
            'claude-3-5-sonnet').
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        exclude_deleted (bool | Unset): Whether to exclude deleted prompt versions from the
            results. Default is False. Default: False.
        min_version (int | None | Unset): Minimum version number to filter on (inclusive).
        max_version (int | None | Unset): Maximum version number to filter on (inclusive).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LLMEvalsVersionListResponse]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
eval_name=eval_name,
sort=sort,
page_size=page_size,
page=page,
model_provider=model_provider,
model_name=model_name,
created_after=created_after,
created_before=created_before,
exclude_deleted=exclude_deleted,
min_version=min_version,
max_version=max_version,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: UUID,
    eval_name: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    model_provider: None | str | Unset = UNSET,
    model_name: None | str | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,
    exclude_deleted: bool | Unset = False,
    min_version: int | None | Unset = UNSET,
    max_version: int | None | Unset = UNSET,

) -> HTTPValidationError | LLMEvalsVersionListResponse | None:
    """ List all versions of an llm eval

     List all versions of an llm eval with optional filtering.

    Args:
        task_id (UUID):
        eval_name (str): The name of the llm eval to retrieve.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        model_provider (None | str | Unset): Filter by model provider (e.g., 'openai',
            'anthropic', 'azure').
        model_name (None | str | Unset): Filter by model name (e.g., 'gpt-4',
            'claude-3-5-sonnet').
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        exclude_deleted (bool | Unset): Whether to exclude deleted prompt versions from the
            results. Default is False. Default: False.
        min_version (int | None | Unset): Minimum version number to filter on (inclusive).
        max_version (int | None | Unset): Maximum version number to filter on (inclusive).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LLMEvalsVersionListResponse
     """


    return (await asyncio_detailed(
        task_id=task_id,
eval_name=eval_name,
client=client,
sort=sort,
page_size=page_size,
page=page,
model_provider=model_provider,
model_name=model_name,
created_after=created_after,
created_before=created_before,
exclude_deleted=exclude_deleted,
min_version=min_version,
max_version=max_version,

    )).parsed
