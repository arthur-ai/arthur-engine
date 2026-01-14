from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.continuous_eval_run_status import ContinuousEvalRunStatus
from ...models.http_validation_error import HTTPValidationError
from ...models.list_agentic_annotations_response import ListAgenticAnnotationsResponse
from ...models.pagination_sort_method import PaginationSortMethod
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    trace_id: str,
    *,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    continuous_eval_id: None | str | Unset = UNSET,
    annotation_type: None | str | Unset = UNSET,
    annotation_score: int | None | Unset = UNSET,
    run_status: ContinuousEvalRunStatus | None | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_sort: str | Unset = UNSET
    if not isinstance(sort, Unset):
        json_sort = sort.value

    params["sort"] = json_sort

    params["page_size"] = page_size

    params["page"] = page

    json_continuous_eval_id: None | str | Unset
    if isinstance(continuous_eval_id, Unset):
        json_continuous_eval_id = UNSET
    else:
        json_continuous_eval_id = continuous_eval_id
    params["continuous_eval_id"] = json_continuous_eval_id

    json_annotation_type: None | str | Unset
    if isinstance(annotation_type, Unset):
        json_annotation_type = UNSET
    else:
        json_annotation_type = annotation_type
    params["annotation_type"] = json_annotation_type

    json_annotation_score: int | None | Unset
    if isinstance(annotation_score, Unset):
        json_annotation_score = UNSET
    else:
        json_annotation_score = annotation_score
    params["annotation_score"] = json_annotation_score

    json_run_status: None | str | Unset
    if isinstance(run_status, Unset):
        json_run_status = UNSET
    elif isinstance(run_status, ContinuousEvalRunStatus):
        json_run_status = run_status.value
    else:
        json_run_status = run_status
    params["run_status"] = json_run_status

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


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/traces/{trace_id}/annotations".format(trace_id=quote(str(trace_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ListAgenticAnnotationsResponse | None:
    if response.status_code == 200:
        response_200 = ListAgenticAnnotationsResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ListAgenticAnnotationsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    trace_id: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    continuous_eval_id: None | str | Unset = UNSET,
    annotation_type: None | str | Unset = UNSET,
    annotation_score: int | None | Unset = UNSET,
    run_status: ContinuousEvalRunStatus | None | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> Response[HTTPValidationError | ListAgenticAnnotationsResponse]:
    """ List Annotations for a Trace

     List annotations for a trace

    Args:
        trace_id (str):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        continuous_eval_id (None | str | Unset): ID of the continuous eval to filter on.
        annotation_type (None | str | Unset): Annotation type to filter on.
        annotation_score (int | None | Unset): Annotation score to filter on.
        run_status (ContinuousEvalRunStatus | None | Unset): Run status to filter on.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListAgenticAnnotationsResponse]
     """


    kwargs = _get_kwargs(
        trace_id=trace_id,
sort=sort,
page_size=page_size,
page=page,
continuous_eval_id=continuous_eval_id,
annotation_type=annotation_type,
annotation_score=annotation_score,
run_status=run_status,
created_after=created_after,
created_before=created_before,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    trace_id: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    continuous_eval_id: None | str | Unset = UNSET,
    annotation_type: None | str | Unset = UNSET,
    annotation_score: int | None | Unset = UNSET,
    run_status: ContinuousEvalRunStatus | None | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> HTTPValidationError | ListAgenticAnnotationsResponse | None:
    """ List Annotations for a Trace

     List annotations for a trace

    Args:
        trace_id (str):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        continuous_eval_id (None | str | Unset): ID of the continuous eval to filter on.
        annotation_type (None | str | Unset): Annotation type to filter on.
        annotation_score (int | None | Unset): Annotation score to filter on.
        run_status (ContinuousEvalRunStatus | None | Unset): Run status to filter on.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListAgenticAnnotationsResponse
     """


    return sync_detailed(
        trace_id=trace_id,
client=client,
sort=sort,
page_size=page_size,
page=page,
continuous_eval_id=continuous_eval_id,
annotation_type=annotation_type,
annotation_score=annotation_score,
run_status=run_status,
created_after=created_after,
created_before=created_before,

    ).parsed

async def asyncio_detailed(
    trace_id: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    continuous_eval_id: None | str | Unset = UNSET,
    annotation_type: None | str | Unset = UNSET,
    annotation_score: int | None | Unset = UNSET,
    run_status: ContinuousEvalRunStatus | None | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> Response[HTTPValidationError | ListAgenticAnnotationsResponse]:
    """ List Annotations for a Trace

     List annotations for a trace

    Args:
        trace_id (str):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        continuous_eval_id (None | str | Unset): ID of the continuous eval to filter on.
        annotation_type (None | str | Unset): Annotation type to filter on.
        annotation_score (int | None | Unset): Annotation score to filter on.
        run_status (ContinuousEvalRunStatus | None | Unset): Run status to filter on.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ListAgenticAnnotationsResponse]
     """


    kwargs = _get_kwargs(
        trace_id=trace_id,
sort=sort,
page_size=page_size,
page=page,
continuous_eval_id=continuous_eval_id,
annotation_type=annotation_type,
annotation_score=annotation_score,
run_status=run_status,
created_after=created_after,
created_before=created_before,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    trace_id: str,
    *,
    client: AuthenticatedClient,
    sort: PaginationSortMethod | Unset = UNSET,
    page_size: int | Unset = 10,
    page: int | Unset = 0,
    continuous_eval_id: None | str | Unset = UNSET,
    annotation_type: None | str | Unset = UNSET,
    annotation_score: int | None | Unset = UNSET,
    run_status: ContinuousEvalRunStatus | None | Unset = UNSET,
    created_after: None | str | Unset = UNSET,
    created_before: None | str | Unset = UNSET,

) -> HTTPValidationError | ListAgenticAnnotationsResponse | None:
    """ List Annotations for a Trace

     List annotations for a trace

    Args:
        trace_id (str):
        sort (PaginationSortMethod | Unset):
        page_size (int | Unset): Page size. Default is 10. Must be greater than 0 and less than
            5000. Default: 10.
        page (int | Unset): Page number Default: 0.
        continuous_eval_id (None | str | Unset): ID of the continuous eval to filter on.
        annotation_type (None | str | Unset): Annotation type to filter on.
        annotation_score (int | None | Unset): Annotation score to filter on.
        run_status (ContinuousEvalRunStatus | None | Unset): Run status to filter on.
        created_after (None | str | Unset): Inclusive start date for prompt creation in ISO8601
            string format. Use local time (not UTC).
        created_before (None | str | Unset): Exclusive end date for prompt creation in ISO8601
            string format. Use local time (not UTC).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ListAgenticAnnotationsResponse
     """


    return (await asyncio_detailed(
        trace_id=trace_id,
client=client,
sort=sort,
page_size=page_size,
page=page,
continuous_eval_id=continuous_eval_id,
annotation_type=annotation_type,
annotation_score=annotation_score,
run_status=run_status,
created_after=created_after,
created_before=created_before,

    )).parsed
