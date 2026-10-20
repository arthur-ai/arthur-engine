"""CloudWatch Logs `FilterLogEvents`, as far as a network scan needs it.

ONE LOG GROUP AT A TIME, PAGED. Each call returns up to 10,000 events and a
`nextToken`; a page can be empty and still carry a token, so paging ends only when the
token does. The engine applies the extraction regex, not AWS: the pattern's dialect is
the one the Platform validated, and the run-time guard (`extractor`) is ours.

WHAT A REFUSAL MEANS IS IN THE ERROR CODE, NOT THE STATUS. The CloudWatch Logs JSON
protocol answers 400 for a rejected signature and for a missing permission alike, so
`with_vendor_status` sets the status the code means on botocore's own exception and
re-raises it unwrapped, as the Vertex connector does for Google's.

The credential needs `logs:FilterLogEvents` on the log groups, and `sts:AssumeRole` on
`role_arn` when one is set. Nothing else.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)

from discovery.retry import MAX_ATTEMPTS, backoff_seconds
from job_executors.discovery_scan import DiscoveryConfigurationError

# Each applies on its own and every call is one page, so together they stay well under
# Test Connection's 120 s preview deadline (PREVIEW_DEADLINE_SECONDS).
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 30.0

PAGE_LIMIT = 10_000
ROLE_SESSION_SECONDS = 3600

_REFUSED_CREDENTIAL = frozenset(
    {
        "UnrecognizedClientException",
        "InvalidClientTokenId",
        "InvalidSignatureException",
        "SignatureDoesNotMatch",
        "IncompleteSignature",
        "ExpiredToken",
        "ExpiredTokenException",
        "InvalidAccessKeyId",
        "AuthFailure",
    }
)
_DENIED = frozenset({"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"})
_PASSING = frozenset(
    {
        "ThrottlingException",
        "Throttling",
        "TooManyRequestsException",
        "LimitExceededException",
        "ServiceUnavailableException",
        "RequestLimitExceeded",
    }
)


class CloudWatchLogsError(Exception):
    """CloudWatch Logs answered, but not with what `FilterLogEvents` returns.

    `status_code` is 200: AWS accepted the call. A refused call is botocore's
    `ClientError`, annotated by `with_vendor_status`.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class CloudWatchLogsSettings:
    """Where the logs are and whose credential reads them."""

    region: str
    log_groups: tuple[str, ...]
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = field(default=None, repr=False)
    role_arn: Optional[str] = None
    external_id: Optional[str] = None


@dataclass(frozen=True)
class LogEvent:
    message: str
    timestamp_ms: int


def logs_client_for(settings: CloudWatchLogsSettings) -> Any:
    """A boto3 `logs` client for the source's region and credential, with botocore's
    retries off: `discovery.retry` owns them, so a stop check runs between attempts."""
    config = Config(
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
        read_timeout=READ_TIMEOUT_SECONDS,
        retries={"total_max_attempts": 1},
    )
    session = boto3.session.Session(
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name=settings.region,
    )
    if settings.role_arn:
        args: dict[str, Any] = {
            "RoleArn": settings.role_arn,
            "RoleSessionName": "arthur-discovery-cloudwatch-logs",
            "DurationSeconds": ROLE_SESSION_SECONDS,
        }
        if settings.external_id:
            args["ExternalId"] = settings.external_id
        sts = session.client("sts", region_name=settings.region, config=config)
        with with_vendor_status("STS AssumeRole"):
            assumed = sts.assume_role(**args)
        creds = assumed["Credentials"]
        session = boto3.session.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=settings.region,
        )
    return session.client("logs", region_name=settings.region, config=config)


class CloudWatchLogsClient:
    """One region, one credential. Pages the events of one log group at a time."""

    def __init__(
        self,
        settings: CloudWatchLogsSettings,
        logger: Optional[logging.Logger] = None,
        logs: Optional[Any] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._sleep = sleep
        self._logs = logs if logs is not None else logs_client_for(settings)

    def events(
        self,
        log_group: str,
        start_ms: int,
        end_ms: int,
        should_stop: Callable[[], bool],
    ) -> Iterator[list[LogEvent]]:
        """Every event of `log_group` in [start_ms, end_ms), a page at a time.

        Stops before the next page once `should_stop` says so.
        """
        token: Optional[str] = None
        while True:
            if should_stop():
                return
            kwargs: dict[str, Any] = {
                "logGroupIdentifier": log_group,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": PAGE_LIMIT,
            }
            if token:
                kwargs["nextToken"] = token
            body = self._page(log_group, kwargs)
            raw = body.get("events")
            if not isinstance(raw, list):
                raise CloudWatchLogsError(
                    "CloudWatch Logs answered FilterLogEvents without an events list",
                    status_code=200,
                )
            yield [event for event in map(_event, raw) if event is not None]
            next_token = body.get("nextToken")
            if not next_token or next_token == token:
                return
            token = next_token

    def _page(self, log_group: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """One page, retried while AWS says the request did no work or the network
        dropped it: `FilterLogEvents` only reads, so a repeat is harmless."""
        refusal: Optional[str] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with with_vendor_status("FilterLogEvents"):
                    body = self._logs.filter_log_events(**kwargs)
            except ClientError as exc:
                if _code(exc) in _PASSING and attempt < MAX_ATTEMPTS:
                    self._sleep(backoff_seconds(attempt, None))
                    continue
                refusal = _log_group_refusal(exc, log_group, self._s.region)
                if refusal is None:
                    raise
                break
            except (ConnectionError, TimeoutError):
                if attempt < MAX_ATTEMPTS:
                    self._sleep(backoff_seconds(attempt, None))
                    continue
                raise
            if not isinstance(body, dict):
                raise CloudWatchLogsError(
                    f"CloudWatch Logs answered FilterLogEvents with a "
                    f"{type(body).__name__} where an object was expected",
                    status_code=200,
                )
            return body
        # Raised outside the except, so the 400 is not even its __context__: Test
        # Connection would find a status there and read the log group's fault as AWS's.
        assert refusal is not None
        raise DiscoveryConfigurationError(refusal)


@contextmanager
def with_vendor_status(operation: str) -> Iterator[None]:
    """Give an AWS failure the meaning the scan and Test Connection report.

    A refused call keeps botocore's `ClientError`, with `status_code` set to what its
    error code means. A host never reached becomes the builtin `ConnectionError` or
    `TimeoutError`, chained from botocore's, whose transport errors derive from neither
    and would otherwise read as AWS failing rather than as the network. No credential
    at all is the source's configuration.
    """
    try:
        yield
    except ClientError as exc:
        setattr(exc, "status_code", _status_for(exc))
        raise
    except (NoCredentialsError, PartialCredentialsError):
        raise DiscoveryConfigurationError(
            f"{operation}: no AWS credential to sign with. Set access_key_id and "
            f"secret_access_key on the source, or let this engine use its own "
            f"credentials (see the source's documentation).",
        ) from None
    except ConnectTimeoutError as exc:
        raise TimeoutError(
            f"{operation}: timed out connecting to AWS: {exc}. The engine needs a "
            f"network path to the CloudWatch Logs endpoint for the source's region.",
        ) from exc
    except ReadTimeoutError as exc:
        raise TimeoutError(f"{operation}: AWS did not answer in time: {exc}") from exc
    except (EndpointConnectionError, ConnectionClosedError) as exc:
        raise ConnectionError(
            f"{operation}: AWS unreachable: {exc}. The engine needs a network path to "
            f"the CloudWatch Logs endpoint for the source's region.",
        ) from exc


def _code(exc: ClientError) -> str:
    return str((exc.response.get("Error") or {}).get("Code") or "")


def _message(exc: ClientError) -> str:
    return str((exc.response.get("Error") or {}).get("Message") or "")


def _status_for(exc: ClientError) -> Optional[int]:
    code = _code(exc)
    if code in _REFUSED_CREDENTIAL:
        return 401
    if code in _DENIED:
        return 403
    status = (exc.response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return status if isinstance(status, int) else None


def _log_group_refusal(exc: ClientError, log_group: str, region: str) -> Optional[str]:
    """What to tell the admin when AWS refused one of the source's log groups, or None
    when the refusal is not about it. Names the group: it is configuration, not data."""
    code = _code(exc)
    if code == "ResourceNotFoundException":
        return (
            f"CloudWatch Logs has no log group {log_group!r} in {region}. Check "
            f"log_group_names and region; a log group shared from another account "
            f"must be given by ARN."
        )
    if code == "InvalidParameterException":
        return (
            f"CloudWatch Logs refused log group {log_group!r} ({_message(exc)}). "
            f"Check log_group_names."
        )
    return None


def _event(raw: Any) -> Optional[LogEvent]:
    if not isinstance(raw, dict):
        return None
    message = raw.get("message")
    timestamp = raw.get("timestamp")
    if not isinstance(message, str) or not isinstance(timestamp, int):
        return None
    return LogEvent(message=message.rstrip("\n"), timestamp_ms=timestamp)
