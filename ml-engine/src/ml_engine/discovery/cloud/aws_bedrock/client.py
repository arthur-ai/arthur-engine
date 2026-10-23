"""Reading an account's Bedrock agents, AgentCore runtimes and CloudTrail model calls.

Read-only. The actions are `bedrock:ListAgents`, `bedrock-agentcore:ListAgentRuntimes`
and `cloudtrail:LookupEvents`, plus `sts:GetCallerIdentity`, which needs no permission
and names the account.

LIST, NEVER DESCRIBE. `GetAgentRuntime` returns a runtime's environment variables,
which hold whatever its builder put there, secrets included, and `GetAgent` returns the
agent's instruction prompt. Neither is called. A list summary has no agent ARN, so the
ARN is composed from the account, region and agent id in the format AWS documents.

LOOKUPEVENTS IS THROTTLED TO TWO REQUESTS A SECOND PER REGION AND ACCOUNT. Calls are
spaced to that rate, and a `ThrottlingException` is retried here with backoff rather
than by botocore, so retries are not multiplied by botocore's own. The other calls use
botocore's standard retry mode.

WHAT AWS ANSWERED. A refused credential is 401 and a denied action 403, on the
`status_code` `failure_code` reads. A service AWS does not run in a region (AgentCore is
in fewer regions than Bedrock) is an endpoint that cannot be reached; it is raised as
`BedrockError` without a status, for the connector to log against that part.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Mapping, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

from discovery.retry import MAX_ATTEMPTS, backoff_seconds
from job_executors.discovery_scan import DiscoveryConfigurationError

# The model calls a caller record is built from. Everything else Bedrock logs -- listing
# models, managing agents, guardrail edits -- is control-plane work by a person or a
# pipeline, not an agent calling a model.
MODEL_CALL_EVENTS = frozenset(
    {"Converse", "ConverseStream", "InvokeModel", "InvokeModelWithResponseStream"},
)
EVENT_SOURCE = "bedrock.amazonaws.com"

# A streaming call is logged twice: once as the AwsApiCall that opened it, and again as
# an AwsServiceEvent when the stream ends. Only the first is a caller's request.
API_CALL = "AwsApiCall"

# LookupEvents' per-region rate, as the seconds between two requests.
LOOKUP_INTERVAL_SECONDS = 0.5
LOOKUP_PAGE_SIZE = 50

# List APIs' page size, and a cap on pages so a cursor that never ends cannot hold a
# scan forever.
LIST_PAGE_SIZE = 100
MAX_PAGES = 1000

_REFUSED_CODES = frozenset(
    {
        "AuthFailure",
        "ExpiredToken",
        "ExpiredTokenException",
        "IncompleteSignature",
        "InvalidClientTokenId",
        "InvalidSignatureException",
        "SignatureDoesNotMatch",
        "UnrecognizedClientException",
    },
)
_DENIED_CODES = frozenset(
    {"AccessDenied", "AccessDeniedException", "OptInRequired", "UnauthorizedOperation"},
)
_THROTTLED_CODES = frozenset(
    {"ThrottlingException", "Throttling", "TooManyRequestsException"},
)


class BedrockError(RuntimeError):
    """A Bedrock, AgentCore, CloudTrail or STS call failed in a way retrying will not fix.

    `status_code` is 401 or 403 when the credential or its permission is the cause, which
    `failure_code` reads; `code` is AWS's own error code, where there is one.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class Identity:
    """Who the scan runs as: the account, and the partition its ARNs are in."""

    account: str
    partition: str


@dataclass(frozen=True)
class ModelCall:
    """One model call CloudTrail logged, with only what a caller record reads."""

    caller_arn: str
    caller_type: str
    model_id: Optional[str]
    event_time: datetime
    error_code: Optional[str] = None
    """CloudTrail's `errorCode`: set when Bedrock refused the call."""


ClientFactory = Callable[[str, str], Any]


def default_client_factory(session: boto3.Session) -> ClientFactory:
    """`(service, region) -> client`, one client per pair.

    CloudTrail's client does not retry: `BedrockClient` paces and retries LookupEvents
    itself. The rest retry in botocore's standard mode.
    """
    timeouts: dict[str, Any] = {"connect_timeout": 10, "read_timeout": 30}
    standard = Config(retries={"mode": "standard", "max_attempts": 8}, **timeouts)
    paced = Config(retries={"mode": "standard", "max_attempts": 1}, **timeouts)
    clients: dict[tuple[str, str], Any] = {}

    def client_for(service: str, region: str) -> Any:
        if (service, region) not in clients:
            clients[(service, region)] = session.client(
                service,
                region_name=region,
                config=paced if service == "cloudtrail" else standard,
            )
        return clients[(service, region)]

    return client_for


class BedrockClient:
    """Lists a region's agents and runtimes, and reads its model calls from CloudTrail.

    `should_stop` is asked before every request and before every backoff sleep; when it
    answers True the listing ends as if AWS had no more pages.
    """

    def __init__(
        self,
        client_for: ClientFactory,
        logger: Optional[logging.Logger] = None,
        should_stop: Callable[[], bool] = lambda: False,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client_for = client_for
        self._log = logger or logging.getLogger(__name__)
        self._should_stop = should_stop
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_lookup: dict[str, float] = {}

    def identity(self, region: str) -> Identity:
        """The account the credentials belong to. STS answers this for any caller."""
        body = self._call(
            "sts",
            region,
            lambda sts: sts.get_caller_identity(),
        )
        account = str(body.get("Account") or "")
        arn = str(body.get("Arn") or "")
        parts = arn.split(":")
        if not account or len(parts) < 2 or not parts[1]:
            raise BedrockError(
                "STS GetCallerIdentity answered without an account or ARN",
                status_code=200,
            )
        return Identity(account=account, partition=parts[1])

    def agents(self, region: str) -> Iterator[Mapping[str, Any]]:
        """Every Bedrock agent's summary in the region (ListAgents)."""
        yield from self._listing(
            "bedrock-agent",
            region,
            "ListAgents",
            "agentSummaries",
            lambda c, kw: c.list_agents(**kw),
        )

    def agent_runtimes(self, region: str) -> Iterator[Mapping[str, Any]]:
        """Every AgentCore runtime's summary in the region (ListAgentRuntimes)."""
        yield from self._listing(
            "bedrock-agentcore-control",
            region,
            "ListAgentRuntimes",
            "agentRuntimes",
            lambda c, kw: c.list_agent_runtimes(**kw),
        )

    def model_calls(
        self,
        region: str,
        start: datetime,
        end: datetime,
    ) -> Iterator[ModelCall]:
        """The region's Bedrock model calls CloudTrail logged in [start, end).

        LookupEvents takes one lookup attribute, so it is asked for Bedrock's event
        source and the event names are filtered here. A streaming call's
        AwsServiceEvent copy is dropped (see `API_CALL`).
        """
        token: Optional[str] = None
        for _ in range(MAX_PAGES):
            if self._should_stop():
                return
            kwargs: dict[str, Any] = {
                "LookupAttributes": [
                    {"AttributeKey": "EventSource", "AttributeValue": EVENT_SOURCE},
                ],
                "StartTime": start,
                "EndTime": end,
                "MaxResults": LOOKUP_PAGE_SIZE,
            }
            if token:
                kwargs["NextToken"] = token
            page = self._lookup(region, kwargs)
            if page is None:
                return
            for raw in page.get("Events") or []:
                call = _model_call(raw)
                if call is not None:
                    yield call
            next_token = page.get("NextToken")
            if not next_token or next_token == token:
                return
            token = next_token
        self._log.warning(
            "CloudTrail in %s: stopped after %s pages of LookupEvents; the caller list "
            "for this region is incomplete",
            region,
            MAX_PAGES,
        )

    # --- transport ----------------------------------------------------------------

    def _listing(
        self,
        service: str,
        region: str,
        operation: str,
        key: str,
        call: Callable[[Any, dict[str, Any]], Any],
    ) -> Iterator[Mapping[str, Any]]:
        token: Optional[str] = None
        for _ in range(MAX_PAGES):
            if self._should_stop():
                return
            kwargs: dict[str, Any] = {"maxResults": LIST_PAGE_SIZE}
            if token:
                kwargs["nextToken"] = token
            page = self._call(service, region, lambda c: call(c, kwargs))
            items = page.get(key)
            if not isinstance(items, list):
                raise BedrockError(
                    f"{operation} in {region} answered without a {key} list",
                    status_code=200,
                )
            yield from items
            next_token = page.get("nextToken")
            if not next_token or next_token == token:
                return
            token = next_token
        self._log.warning(
            "%s in %s: stopped after %s pages; the list is incomplete",
            operation,
            region,
            MAX_PAGES,
        )

    def _lookup(self, region: str, kwargs: dict[str, Any]) -> Optional[Any]:
        """One LookupEvents page, paced and retried while throttled. None if stopped."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            wait = self._last_lookup.get(region, float("-inf")) + (
                LOOKUP_INTERVAL_SECONDS - self._monotonic()
            )
            if wait > 0:
                self._sleep(wait)
            self._last_lookup[region] = self._monotonic()
            try:
                return self._client_for("cloudtrail", region).lookup_events(**kwargs)
            except ClientError as e:
                code = str((e.response.get("Error") or {}).get("Code") or "")
                if code in _THROTTLED_CODES and attempt < MAX_ATTEMPTS:
                    if self._should_stop():
                        return None
                    self._sleep(backoff_seconds(attempt, None))
                    continue
                raise _error("cloudtrail", region, e) from None
            except BotoCoreError as e:
                raise _error("cloudtrail", region, e) from None
        raise AssertionError("unreachable: the last attempt returns or raises")

    def _call(self, service: str, region: str, call: Callable[[Any], Any]) -> Any:
        try:
            return call(self._client_for(service, region))
        except (ClientError, BotoCoreError) as e:
            raise _error(service, region, e) from None


def _model_call(raw: Mapping[str, Any]) -> Optional[ModelCall]:
    """The call one LookupEvents event records, or None if it is not a model call.

    The caller is the role a session was issued from, not the session: every run of a
    workload gets a new session name, and one role is one workload. An IAM user has no
    session issuer and is named by its own ARN.
    """
    if raw.get("EventName") not in MODEL_CALL_EVENTS:
        return None
    try:
        detail = json.loads(raw.get("CloudTrailEvent") or "")
    except (TypeError, ValueError):
        return None
    if not isinstance(detail, dict) or detail.get("eventType") != API_CALL:
        return None
    if detail.get("eventName") not in MODEL_CALL_EVENTS:
        return None

    who = detail.get("userIdentity") or {}
    issuer = (who.get("sessionContext") or {}).get("sessionIssuer") or {}
    caller = str(issuer.get("arn") or who.get("arn") or "")
    when = _event_time(detail.get("eventTime")) or _as_utc(raw.get("EventTime"))
    if not caller or when is None:
        return None
    model = (detail.get("requestParameters") or {}).get("modelId")
    return ModelCall(
        caller_arn=caller,
        caller_type=str(who.get("type") or ""),
        model_id=str(model) if model else None,
        event_time=when,
        error_code=str(detail.get("errorCode") or "") or None,
    )


def _event_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _as_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _error(service: str, region: str, e: Exception) -> Exception:
    """The client's own error for a botocore failure, with the status `failure_code`
    reads. A missing credential is the source's configuration, not AWS's answer."""
    if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
        return DiscoveryConfigurationError(
            f"Bedrock source has no usable AWS credentials ({e}). Set the source's "
            f"access key, or give this engine credentials of its own.",
        )
    if isinstance(e, ClientError):
        error = e.response.get("Error") or {}
        code = str(error.get("Code") or "")
        message = str(error.get("Message") or "").strip()[:300]
        operation = e.operation_name
        # The role is assumed inside the first call that needs it, so its refusal
        # arrives from that call; it is STS's answer, about the role.
        label = "STS" if operation == "AssumeRole" else service
        status: Optional[int] = None
        if code in _REFUSED_CODES:
            status = 401
        elif code in _DENIED_CODES:
            status = 403
        return BedrockError(
            f"{label} {operation} in {region} failed: {code}"
            f"{': ' + message if message else ''}",
            status_code=status,
            code=code or None,
        )
    return BedrockError(
        f"{service} in {region} could not be reached: {e}. The service may not be "
        f"offered in this region, or the region may not be enabled for the account.",
    )
