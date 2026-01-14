from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.new_rule_request import NewRuleRequest
from ...models.rule_response import RuleResponse
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    body: NewRuleRequest | Unset = UNSET,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v2/default_rules",
    }

    
    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | RuleResponse | None:
    if response.status_code == 200:
        response_200 = RuleResponse.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | RuleResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: NewRuleRequest | Unset = UNSET,

) -> Response[HTTPValidationError | RuleResponse]:
    """ Create Default Rule

     Create a default rule. Default rules are applied universally across existing tasks, subsequently
    created new tasks, and any non-task related requests. Once a rule is created, it is immutable.
    Available rules are 'KeywordRule', 'ModelHallucinationRuleV2', 'ModelSensitiveDataRule',
    'PIIDataRule', 'PromptInjectionRule', 'RegexRule', 'ToxicityRule'. Note: The rules are cached by the
    validation endpoints for 60 seconds.

    Args:
        body (NewRuleRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RuleResponse]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    body: NewRuleRequest | Unset = UNSET,

) -> HTTPValidationError | RuleResponse | None:
    """ Create Default Rule

     Create a default rule. Default rules are applied universally across existing tasks, subsequently
    created new tasks, and any non-task related requests. Once a rule is created, it is immutable.
    Available rules are 'KeywordRule', 'ModelHallucinationRuleV2', 'ModelSensitiveDataRule',
    'PIIDataRule', 'PromptInjectionRule', 'RegexRule', 'ToxicityRule'. Note: The rules are cached by the
    validation endpoints for 60 seconds.

    Args:
        body (NewRuleRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RuleResponse
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: NewRuleRequest | Unset = UNSET,

) -> Response[HTTPValidationError | RuleResponse]:
    """ Create Default Rule

     Create a default rule. Default rules are applied universally across existing tasks, subsequently
    created new tasks, and any non-task related requests. Once a rule is created, it is immutable.
    Available rules are 'KeywordRule', 'ModelHallucinationRuleV2', 'ModelSensitiveDataRule',
    'PIIDataRule', 'PromptInjectionRule', 'RegexRule', 'ToxicityRule'. Note: The rules are cached by the
    validation endpoints for 60 seconds.

    Args:
        body (NewRuleRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RuleResponse]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    body: NewRuleRequest | Unset = UNSET,

) -> HTTPValidationError | RuleResponse | None:
    """ Create Default Rule

     Create a default rule. Default rules are applied universally across existing tasks, subsequently
    created new tasks, and any non-task related requests. Once a rule is created, it is immutable.
    Available rules are 'KeywordRule', 'ModelHallucinationRuleV2', 'ModelSensitiveDataRule',
    'PIIDataRule', 'PromptInjectionRule', 'RegexRule', 'ToxicityRule'. Note: The rules are cached by the
    validation endpoints for 60 seconds.

    Args:
        body (NewRuleRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RuleResponse
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
