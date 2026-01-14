from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.body_upload_embeddings_file_api_chat_files_post import BodyUploadEmbeddingsFileApiChatFilesPost
from ...models.file_upload_result import FileUploadResult
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    body: BodyUploadEmbeddingsFileApiChatFilesPost,
    is_global: bool | Unset = False,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    params: dict[str, Any] = {}

    params["is_global"] = is_global


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/chat/files",
        "params": params,
    }

    _kwargs["files"] = body.to_multipart()



    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> FileUploadResult | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = FileUploadResult.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[FileUploadResult | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: BodyUploadEmbeddingsFileApiChatFilesPost,
    is_global: bool | Unset = False,

) -> Response[FileUploadResult | HTTPValidationError]:
    """ Upload Embeddings File

     Upload files via form-data. Only PDF, CSV, TXT types accepted.

    Args:
        is_global (bool | Unset):  Default: False.
        body (BodyUploadEmbeddingsFileApiChatFilesPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FileUploadResult | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        body=body,
is_global=is_global,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    body: BodyUploadEmbeddingsFileApiChatFilesPost,
    is_global: bool | Unset = False,

) -> FileUploadResult | HTTPValidationError | None:
    """ Upload Embeddings File

     Upload files via form-data. Only PDF, CSV, TXT types accepted.

    Args:
        is_global (bool | Unset):  Default: False.
        body (BodyUploadEmbeddingsFileApiChatFilesPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FileUploadResult | HTTPValidationError
     """


    return sync_detailed(
        client=client,
body=body,
is_global=is_global,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: BodyUploadEmbeddingsFileApiChatFilesPost,
    is_global: bool | Unset = False,

) -> Response[FileUploadResult | HTTPValidationError]:
    """ Upload Embeddings File

     Upload files via form-data. Only PDF, CSV, TXT types accepted.

    Args:
        is_global (bool | Unset):  Default: False.
        body (BodyUploadEmbeddingsFileApiChatFilesPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[FileUploadResult | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        body=body,
is_global=is_global,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: BodyUploadEmbeddingsFileApiChatFilesPost,
    is_global: bool | Unset = False,

) -> FileUploadResult | HTTPValidationError | None:
    """ Upload Embeddings File

     Upload files via form-data. Only PDF, CSV, TXT types accepted.

    Args:
        is_global (bool | Unset):  Default: False.
        body (BodyUploadEmbeddingsFileApiChatFilesPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        FileUploadResult | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
body=body,
is_global=is_global,

    )).parsed
