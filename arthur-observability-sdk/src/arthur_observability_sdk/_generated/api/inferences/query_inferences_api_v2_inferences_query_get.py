from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.query_inferences_response import QueryInferencesResponse
from ...models.rule_result_enum import RuleResultEnum
from ...models.rule_type import RuleType
from ...types import UNSET, Unset
from dateutil.parser import isoparse
from typing import cast
import datetime



def _get_kwargs(
    *,
    task_ids: list[str] | Unset = UNSET,
    task_name: str | Unset = UNSET,
    conversation_id: str | Unset = UNSET,
    inference_id: str | Unset = UNSET,
    user_id: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    rule_types: list[RuleType] | Unset = UNSET,
    rule_statuses: list[RuleResultEnum] | Unset = UNSET,
    prompt_statuses: list[RuleResultEnum] | Unset = UNSET,
    response_statuses: list[RuleResultEnum] | Unset = UNSET,
    include_count: bool | Unset = True,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_task_ids: list[str] | Unset = UNSET
    if not isinstance(task_ids, Unset):
        json_task_ids = task_ids


    params["task_ids"] = json_task_ids

    params["task_name"] = task_name

    params["conversation_id"] = conversation_id

    params["inference_id"] = inference_id

    params["user_id"] = user_id

    json_start_time: str | Unset = UNSET
    if not isinstance(start_time, Unset):
        json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time: str | Unset = UNSET
    if not isinstance(end_time, Unset):
        json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    json_rule_types: list[str] | Unset = UNSET
    if not isinstance(rule_types, Unset):
        json_rule_types = []
        for rule_types_item_data in rule_types:
            rule_types_item = rule_types_item_data.value
            json_rule_types.append(rule_types_item)


    params["rule_types"] = json_rule_types

    json_rule_statuses: list[str] | Unset = UNSET
    if not isinstance(rule_statuses, Unset):
        json_rule_statuses = []
        for rule_statuses_item_data in rule_statuses:
            rule_statuses_item = rule_statuses_item_data.value
            json_rule_statuses.append(rule_statuses_item)


    params["rule_statuses"] = json_rule_statuses

    json_prompt_statuses: list[str] | Unset = UNSET
    if not isinstance(prompt_statuses, Unset):
        json_prompt_statuses = []
        for prompt_statuses_item_data in prompt_statuses:
            prompt_statuses_item = prompt_statuses_item_data.value
            json_prompt_statuses.append(prompt_statuses_item)


    params["prompt_statuses"] = json_prompt_statuses

    json_response_statuses: list[str] | Unset = UNSET
    if not isinstance(response_statuses, Unset):
        json_response_statuses = []
        for response_statuses_item_data in response_statuses:
            response_statuses_item = response_statuses_item_data.value
            json_response_statuses.append(response_statuses_item)


    params["response_statuses"] = json_response_statuses

    params["include_count"] = include_count

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/inferences/query",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | QueryInferencesResponse | None:
    if response.status_code == 200:
        response_200 = QueryInferencesResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | QueryInferencesResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    task_ids: list[str] | Unset = UNSET,
    task_name: str | Unset = UNSET,
    conversation_id: str | Unset = UNSET,
    inference_id: str | Unset = UNSET,
    user_id: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    rule_types: list[RuleType] | Unset = UNSET,
    rule_statuses: list[RuleResultEnum] | Unset = UNSET,
    prompt_statuses: list[RuleResultEnum] | Unset = UNSET,
    response_statuses: list[RuleResultEnum] | Unset = UNSET,
    include_count: bool | Unset = True,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | QueryInferencesResponse]:
    """ Query Inferences

     Paginated inference querying. See parameters for available filters. Includes inferences from
    archived tasks and rules.

    Args:
        task_ids (list[str] | Unset): Task ID to filter on.
        task_name (str | Unset): Task name to filter on.
        conversation_id (str | Unset): Conversation ID to filter on.
        inference_id (str | Unset): Inference ID to filter on.
        user_id (str | Unset): User ID to filter on.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
        rule_types (list[RuleType] | Unset): List of RuleType to query for. Any inference that ran
            any rule in the list will be returned. Defaults to all statuses. If used in conjunction
            with with rule_statuses, will return inferences with rules in the intersection of
            rule_types and rule_statuses.
        rule_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for. Any
            inference with any rule status in the list will be returned. Defaults to all statuses. If
            used in conjunction with with rule_types, will return inferences with rules in the
            intersection of rule_statuses and rule_types.
        prompt_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference prompt stage level. Must be 'Pass' / 'Fail'. Defaults to both.
        response_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference response stage level. Must be 'Pass' / 'Fail'. Defaults to both. Inferences
            missing responses will not be affected by this filter.
        include_count (bool | Unset): Whether to include the total count of matching inferences.
            Set to False to improve query performance for large datasets. Count will be returned as -1
            if set to False. Default: True.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | QueryInferencesResponse]
     """


    kwargs = _get_kwargs(
        task_ids=task_ids,
task_name=task_name,
conversation_id=conversation_id,
inference_id=inference_id,
user_id=user_id,
start_time=start_time,
end_time=end_time,
rule_types=rule_types,
rule_statuses=rule_statuses,
prompt_statuses=prompt_statuses,
response_statuses=response_statuses,
include_count=include_count,
sort=sort,
page_size=page_size,
page=page,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    task_ids: list[str] | Unset = UNSET,
    task_name: str | Unset = UNSET,
    conversation_id: str | Unset = UNSET,
    inference_id: str | Unset = UNSET,
    user_id: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    rule_types: list[RuleType] | Unset = UNSET,
    rule_statuses: list[RuleResultEnum] | Unset = UNSET,
    prompt_statuses: list[RuleResultEnum] | Unset = UNSET,
    response_statuses: list[RuleResultEnum] | Unset = UNSET,
    include_count: bool | Unset = True,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | QueryInferencesResponse | None:
    """ Query Inferences

     Paginated inference querying. See parameters for available filters. Includes inferences from
    archived tasks and rules.

    Args:
        task_ids (list[str] | Unset): Task ID to filter on.
        task_name (str | Unset): Task name to filter on.
        conversation_id (str | Unset): Conversation ID to filter on.
        inference_id (str | Unset): Inference ID to filter on.
        user_id (str | Unset): User ID to filter on.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
        rule_types (list[RuleType] | Unset): List of RuleType to query for. Any inference that ran
            any rule in the list will be returned. Defaults to all statuses. If used in conjunction
            with with rule_statuses, will return inferences with rules in the intersection of
            rule_types and rule_statuses.
        rule_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for. Any
            inference with any rule status in the list will be returned. Defaults to all statuses. If
            used in conjunction with with rule_types, will return inferences with rules in the
            intersection of rule_statuses and rule_types.
        prompt_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference prompt stage level. Must be 'Pass' / 'Fail'. Defaults to both.
        response_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference response stage level. Must be 'Pass' / 'Fail'. Defaults to both. Inferences
            missing responses will not be affected by this filter.
        include_count (bool | Unset): Whether to include the total count of matching inferences.
            Set to False to improve query performance for large datasets. Count will be returned as -1
            if set to False. Default: True.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | QueryInferencesResponse
     """


    return sync_detailed(
        client=client,
task_ids=task_ids,
task_name=task_name,
conversation_id=conversation_id,
inference_id=inference_id,
user_id=user_id,
start_time=start_time,
end_time=end_time,
rule_types=rule_types,
rule_statuses=rule_statuses,
prompt_statuses=prompt_statuses,
response_statuses=response_statuses,
include_count=include_count,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    task_ids: list[str] | Unset = UNSET,
    task_name: str | Unset = UNSET,
    conversation_id: str | Unset = UNSET,
    inference_id: str | Unset = UNSET,
    user_id: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    rule_types: list[RuleType] | Unset = UNSET,
    rule_statuses: list[RuleResultEnum] | Unset = UNSET,
    prompt_statuses: list[RuleResultEnum] | Unset = UNSET,
    response_statuses: list[RuleResultEnum] | Unset = UNSET,
    include_count: bool | Unset = True,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | QueryInferencesResponse]:
    """ Query Inferences

     Paginated inference querying. See parameters for available filters. Includes inferences from
    archived tasks and rules.

    Args:
        task_ids (list[str] | Unset): Task ID to filter on.
        task_name (str | Unset): Task name to filter on.
        conversation_id (str | Unset): Conversation ID to filter on.
        inference_id (str | Unset): Inference ID to filter on.
        user_id (str | Unset): User ID to filter on.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
        rule_types (list[RuleType] | Unset): List of RuleType to query for. Any inference that ran
            any rule in the list will be returned. Defaults to all statuses. If used in conjunction
            with with rule_statuses, will return inferences with rules in the intersection of
            rule_types and rule_statuses.
        rule_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for. Any
            inference with any rule status in the list will be returned. Defaults to all statuses. If
            used in conjunction with with rule_types, will return inferences with rules in the
            intersection of rule_statuses and rule_types.
        prompt_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference prompt stage level. Must be 'Pass' / 'Fail'. Defaults to both.
        response_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference response stage level. Must be 'Pass' / 'Fail'. Defaults to both. Inferences
            missing responses will not be affected by this filter.
        include_count (bool | Unset): Whether to include the total count of matching inferences.
            Set to False to improve query performance for large datasets. Count will be returned as -1
            if set to False. Default: True.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | QueryInferencesResponse]
     """


    kwargs = _get_kwargs(
        task_ids=task_ids,
task_name=task_name,
conversation_id=conversation_id,
inference_id=inference_id,
user_id=user_id,
start_time=start_time,
end_time=end_time,
rule_types=rule_types,
rule_statuses=rule_statuses,
prompt_statuses=prompt_statuses,
response_statuses=response_statuses,
include_count=include_count,
sort=sort,
page_size=page_size,
page=page,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    task_ids: list[str] | Unset = UNSET,
    task_name: str | Unset = UNSET,
    conversation_id: str | Unset = UNSET,
    inference_id: str | Unset = UNSET,
    user_id: str | Unset = UNSET,
    start_time: datetime.datetime | Unset = UNSET,
    end_time: datetime.datetime | Unset = UNSET,
    rule_types: list[RuleType] | Unset = UNSET,
    rule_statuses: list[RuleResultEnum] | Unset = UNSET,
    prompt_statuses: list[RuleResultEnum] | Unset = UNSET,
    response_statuses: list[RuleResultEnum] | Unset = UNSET,
    include_count: bool | Unset = True,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | QueryInferencesResponse | None:
    """ Query Inferences

     Paginated inference querying. See parameters for available filters. Includes inferences from
    archived tasks and rules.

    Args:
        task_ids (list[str] | Unset): Task ID to filter on.
        task_name (str | Unset): Task name to filter on.
        conversation_id (str | Unset): Conversation ID to filter on.
        inference_id (str | Unset): Inference ID to filter on.
        user_id (str | Unset): User ID to filter on.
        start_time (datetime.datetime | Unset): Inclusive start date in ISO8601 string format.
        end_time (datetime.datetime | Unset): Exclusive end date in ISO8601 string format.
        rule_types (list[RuleType] | Unset): List of RuleType to query for. Any inference that ran
            any rule in the list will be returned. Defaults to all statuses. If used in conjunction
            with with rule_statuses, will return inferences with rules in the intersection of
            rule_types and rule_statuses.
        rule_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for. Any
            inference with any rule status in the list will be returned. Defaults to all statuses. If
            used in conjunction with with rule_types, will return inferences with rules in the
            intersection of rule_statuses and rule_types.
        prompt_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference prompt stage level. Must be 'Pass' / 'Fail'. Defaults to both.
        response_statuses (list[RuleResultEnum] | Unset): List of RuleResultEnum to query for at
            inference response stage level. Must be 'Pass' / 'Fail'. Defaults to both. Inferences
            missing responses will not be affected by this filter.
        include_count (bool | Unset): Whether to include the total count of matching inferences.
            Set to False to improve query performance for large datasets. Count will be returned as -1
            if set to False. Default: True.
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | QueryInferencesResponse
     """


    return (await asyncio_detailed(
        client=client,
task_ids=task_ids,
task_name=task_name,
conversation_id=conversation_id,
inference_id=inference_id,
user_id=user_id,
start_time=start_time,
end_time=end_time,
rule_types=rule_types,
rule_statuses=rule_statuses,
prompt_statuses=prompt_statuses,
response_statuses=response_statuses,
include_count=include_count,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
