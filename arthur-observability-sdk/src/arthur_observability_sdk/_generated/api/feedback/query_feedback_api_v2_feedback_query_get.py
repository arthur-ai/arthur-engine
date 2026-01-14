from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.inference_feedback_target import InferenceFeedbackTarget
from ...models.pagination_sort_method import PaginationSortMethod
from ...models.query_feedback_response import QueryFeedbackResponse
from ...types import UNSET, Unset
from dateutil.parser import isoparse
from typing import cast
import datetime



def _get_kwargs(
    *,
    start_time: datetime.datetime | None | Unset = UNSET,
    end_time: datetime.datetime | None | Unset = UNSET,
    feedback_id: list[str] | None | str | Unset = UNSET,
    inference_id: list[str] | None | str | Unset = UNSET,
    target: InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset = UNSET,
    score: int | list[int] | None | Unset = UNSET,
    feedback_user_id: None | str | Unset = UNSET,
    conversation_id: list[str] | None | str | Unset = UNSET,
    task_id: list[str] | None | str | Unset = UNSET,
    inference_user_id: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_start_time: None | str | Unset
    if isinstance(start_time, Unset):
        json_start_time = UNSET
    elif isinstance(start_time, datetime.datetime):
        json_start_time = start_time.isoformat()
    else:
        json_start_time = start_time
    params["start_time"] = json_start_time

    json_end_time: None | str | Unset
    if isinstance(end_time, Unset):
        json_end_time = UNSET
    elif isinstance(end_time, datetime.datetime):
        json_end_time = end_time.isoformat()
    else:
        json_end_time = end_time
    params["end_time"] = json_end_time

    json_feedback_id: list[str] | None | str | Unset
    if isinstance(feedback_id, Unset):
        json_feedback_id = UNSET
    elif isinstance(feedback_id, list):
        json_feedback_id = feedback_id


    else:
        json_feedback_id = feedback_id
    params["feedback_id"] = json_feedback_id

    json_inference_id: list[str] | None | str | Unset
    if isinstance(inference_id, Unset):
        json_inference_id = UNSET
    elif isinstance(inference_id, list):
        json_inference_id = inference_id


    else:
        json_inference_id = inference_id
    params["inference_id"] = json_inference_id

    json_target: list[str] | None | str | Unset
    if isinstance(target, Unset):
        json_target = UNSET
    elif isinstance(target, InferenceFeedbackTarget):
        json_target = target.value
    elif isinstance(target, list):
        json_target = []
        for target_type_1_item_data in target:
            target_type_1_item = target_type_1_item_data.value
            json_target.append(target_type_1_item)


    else:
        json_target = target
    params["target"] = json_target

    json_score: int | list[int] | None | Unset
    if isinstance(score, Unset):
        json_score = UNSET
    elif isinstance(score, list):
        json_score = score


    else:
        json_score = score
    params["score"] = json_score

    json_feedback_user_id: None | str | Unset
    if isinstance(feedback_user_id, Unset):
        json_feedback_user_id = UNSET
    else:
        json_feedback_user_id = feedback_user_id
    params["feedback_user_id"] = json_feedback_user_id

    json_conversation_id: list[str] | None | str | Unset
    if isinstance(conversation_id, Unset):
        json_conversation_id = UNSET
    elif isinstance(conversation_id, list):
        json_conversation_id = conversation_id


    else:
        json_conversation_id = conversation_id
    params["conversation_id"] = json_conversation_id

    json_task_id: list[str] | None | str | Unset
    if isinstance(task_id, Unset):
        json_task_id = UNSET
    elif isinstance(task_id, list):
        json_task_id = task_id


    else:
        json_task_id = task_id
    params["task_id"] = json_task_id

    json_inference_user_id: None | str | Unset
    if isinstance(inference_user_id, Unset):
        json_inference_user_id = UNSET
    else:
        json_inference_user_id = inference_user_id
    params["inference_user_id"] = json_inference_user_id

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v2/feedback/query",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | QueryFeedbackResponse | None:
    if response.status_code == 200:
        response_200 = QueryFeedbackResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | QueryFeedbackResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    start_time: datetime.datetime | None | Unset = UNSET,
    end_time: datetime.datetime | None | Unset = UNSET,
    feedback_id: list[str] | None | str | Unset = UNSET,
    inference_id: list[str] | None | str | Unset = UNSET,
    target: InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset = UNSET,
    score: int | list[int] | None | Unset = UNSET,
    feedback_user_id: None | str | Unset = UNSET,
    conversation_id: list[str] | None | str | Unset = UNSET,
    task_id: list[str] | None | str | Unset = UNSET,
    inference_user_id: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | QueryFeedbackResponse]:
    """ Query Feedback

     Paginated feedback querying. See parameters for available filters. Includes feedback from archived
    tasks and rules.

    Args:
        start_time (datetime.datetime | None | Unset): Inclusive start date in ISO8601 string
            format
        end_time (datetime.datetime | None | Unset): Exclusive end date in ISO8601 string format
        feedback_id (list[str] | None | str | Unset): Feedback ID to filter on
        inference_id (list[str] | None | str | Unset): Inference ID to filter on
        target (InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset): Target of
            the feedback. Must be one of ['context', 'response_results', 'prompt_results']
        score (int | list[int] | None | Unset): Score of the feedback. Must be an integer.
        feedback_user_id (None | str | Unset): User ID of the user giving feedback to filter on
            (query will perform fuzzy search)
        conversation_id (list[str] | None | str | Unset): Conversation ID to filter on
        task_id (list[str] | None | str | Unset): Task ID to filter on
        inference_user_id (None | str | Unset): User ID of the user who created the inferences to
            filter on (query will perform fuzzy search)
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | QueryFeedbackResponse]
     """


    kwargs = _get_kwargs(
        start_time=start_time,
end_time=end_time,
feedback_id=feedback_id,
inference_id=inference_id,
target=target,
score=score,
feedback_user_id=feedback_user_id,
conversation_id=conversation_id,
task_id=task_id,
inference_user_id=inference_user_id,
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
    start_time: datetime.datetime | None | Unset = UNSET,
    end_time: datetime.datetime | None | Unset = UNSET,
    feedback_id: list[str] | None | str | Unset = UNSET,
    inference_id: list[str] | None | str | Unset = UNSET,
    target: InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset = UNSET,
    score: int | list[int] | None | Unset = UNSET,
    feedback_user_id: None | str | Unset = UNSET,
    conversation_id: list[str] | None | str | Unset = UNSET,
    task_id: list[str] | None | str | Unset = UNSET,
    inference_user_id: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | QueryFeedbackResponse | None:
    """ Query Feedback

     Paginated feedback querying. See parameters for available filters. Includes feedback from archived
    tasks and rules.

    Args:
        start_time (datetime.datetime | None | Unset): Inclusive start date in ISO8601 string
            format
        end_time (datetime.datetime | None | Unset): Exclusive end date in ISO8601 string format
        feedback_id (list[str] | None | str | Unset): Feedback ID to filter on
        inference_id (list[str] | None | str | Unset): Inference ID to filter on
        target (InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset): Target of
            the feedback. Must be one of ['context', 'response_results', 'prompt_results']
        score (int | list[int] | None | Unset): Score of the feedback. Must be an integer.
        feedback_user_id (None | str | Unset): User ID of the user giving feedback to filter on
            (query will perform fuzzy search)
        conversation_id (list[str] | None | str | Unset): Conversation ID to filter on
        task_id (list[str] | None | str | Unset): Task ID to filter on
        inference_user_id (None | str | Unset): User ID of the user who created the inferences to
            filter on (query will perform fuzzy search)
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | QueryFeedbackResponse
     """


    return sync_detailed(
        client=client,
start_time=start_time,
end_time=end_time,
feedback_id=feedback_id,
inference_id=inference_id,
target=target,
score=score,
feedback_user_id=feedback_user_id,
conversation_id=conversation_id,
task_id=task_id,
inference_user_id=inference_user_id,
sort=sort,
page_size=page_size,
page=page,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    start_time: datetime.datetime | None | Unset = UNSET,
    end_time: datetime.datetime | None | Unset = UNSET,
    feedback_id: list[str] | None | str | Unset = UNSET,
    inference_id: list[str] | None | str | Unset = UNSET,
    target: InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset = UNSET,
    score: int | list[int] | None | Unset = UNSET,
    feedback_user_id: None | str | Unset = UNSET,
    conversation_id: list[str] | None | str | Unset = UNSET,
    task_id: list[str] | None | str | Unset = UNSET,
    inference_user_id: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> Response[HTTPValidationError | QueryFeedbackResponse]:
    """ Query Feedback

     Paginated feedback querying. See parameters for available filters. Includes feedback from archived
    tasks and rules.

    Args:
        start_time (datetime.datetime | None | Unset): Inclusive start date in ISO8601 string
            format
        end_time (datetime.datetime | None | Unset): Exclusive end date in ISO8601 string format
        feedback_id (list[str] | None | str | Unset): Feedback ID to filter on
        inference_id (list[str] | None | str | Unset): Inference ID to filter on
        target (InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset): Target of
            the feedback. Must be one of ['context', 'response_results', 'prompt_results']
        score (int | list[int] | None | Unset): Score of the feedback. Must be an integer.
        feedback_user_id (None | str | Unset): User ID of the user giving feedback to filter on
            (query will perform fuzzy search)
        conversation_id (list[str] | None | str | Unset): Conversation ID to filter on
        task_id (list[str] | None | str | Unset): Task ID to filter on
        inference_user_id (None | str | Unset): User ID of the user who created the inferences to
            filter on (query will perform fuzzy search)
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | QueryFeedbackResponse]
     """


    kwargs = _get_kwargs(
        start_time=start_time,
end_time=end_time,
feedback_id=feedback_id,
inference_id=inference_id,
target=target,
score=score,
feedback_user_id=feedback_user_id,
conversation_id=conversation_id,
task_id=task_id,
inference_user_id=inference_user_id,
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
    start_time: datetime.datetime | None | Unset = UNSET,
    end_time: datetime.datetime | None | Unset = UNSET,
    feedback_id: list[str] | None | str | Unset = UNSET,
    inference_id: list[str] | None | str | Unset = UNSET,
    target: InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset = UNSET,
    score: int | list[int] | None | Unset = UNSET,
    feedback_user_id: None | str | Unset = UNSET,
    conversation_id: list[str] | None | str | Unset = UNSET,
    task_id: list[str] | None | str | Unset = UNSET,
    inference_user_id: None | str | Unset = UNSET,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,

) -> HTTPValidationError | QueryFeedbackResponse | None:
    """ Query Feedback

     Paginated feedback querying. See parameters for available filters. Includes feedback from archived
    tasks and rules.

    Args:
        start_time (datetime.datetime | None | Unset): Inclusive start date in ISO8601 string
            format
        end_time (datetime.datetime | None | Unset): Exclusive end date in ISO8601 string format
        feedback_id (list[str] | None | str | Unset): Feedback ID to filter on
        inference_id (list[str] | None | str | Unset): Inference ID to filter on
        target (InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None | Unset): Target of
            the feedback. Must be one of ['context', 'response_results', 'prompt_results']
        score (int | list[int] | None | Unset): Score of the feedback. Must be an integer.
        feedback_user_id (None | str | Unset): User ID of the user giving feedback to filter on
            (query will perform fuzzy search)
        conversation_id (list[str] | None | str | Unset): Conversation ID to filter on
        task_id (list[str] | None | str | Unset): Task ID to filter on
        inference_user_id (None | str | Unset): User ID of the user who created the inferences to
            filter on (query will perform fuzzy search)
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | QueryFeedbackResponse
     """


    return (await asyncio_detailed(
        client=client,
start_time=start_time,
end_time=end_time,
feedback_id=feedback_id,
inference_id=inference_id,
target=target,
score=score,
feedback_user_id=feedback_user_id,
conversation_id=conversation_id,
task_id=task_id,
inference_user_id=inference_user_id,
sort=sort,
page_size=page_size,
page=page,

    )).parsed
