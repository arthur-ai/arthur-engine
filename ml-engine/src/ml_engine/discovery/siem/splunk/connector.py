"""Splunk Enterprise's side of a DISCOVER_AGENTS scan.

Runs the source config's SPL as a search job over the scan's lookback, checks the
result's columns against the output contract, and hands each page of rows onward as
records. What a row MEANS is the customer's query's business: it names the columns
through `table`/`rename`, and nothing here maps fields.

BATCHED PER RESULTS PAGE, BECAUSE THAT IS THE UNIT THAT ARRIVES. A scan that fails on
its third page has already published the first two.
"""

import logging
import time
from typing import Callable, Iterator, Mapping, Optional, Sequence
from urllib.parse import urlsplit

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from discovery.siem.records import records_from_rows, require_contract_columns
from discovery.siem.splunk.client import (
    JobStatus,
    SplunkClient,
    SplunkSettings,
    wait_for_job,
)
from discovery.siem.tls import parse_tls_verification

VENDOR = "splunk_enterprise"

BASE_URL_FIELD = "base_url"
AUTH_TOKEN_FIELD = "auth_token"
CA_CERTIFICATE_FIELD = "ca_certificate"
TLS_VERIFICATION_FIELD = "tls_verification"

# A search queued this long is not going to start: the token's user is at its quota.
QUEUED_LIMIT_SECONDS = 600.0

ClientFactory = Callable[[SplunkSettings, logging.Logger], SplunkClient]


def _default_client(settings: SplunkSettings, logger: logging.Logger) -> SplunkClient:
    return SplunkClient(settings, logger=logger)


class SplunkConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`, and accepts a
    stop check the way `AcceptsStopCheck` describes.

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    def __init__(
        self,
        client_factory: ClientFactory = _default_client,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client_factory = client_factory
        self._sleep = sleep
        self._clock = clock
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        self._should_stop = should_stop

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """`logger` is the JOB's, so what this reports reaches the Platform job log."""
        settings = settings_from(credentials, source_fields)
        query = search_text(config.query)
        instance = _instance(settings.base_url)
        subject = f"Source config '{config.name}' ({VENDOR})"
        client = self._client_factory(settings, logger)

        # The scan's lookback is the search's time range. It is passed beside the
        # query, never written into it: the SPL stays exactly what the customer wrote.
        earliest = f"-{lookback_hours}h" if lookback_hours > 0 else None
        logger.info(
            "Splunk scan starting against %s, lookback %s",
            instance,
            f"{lookback_hours}h" if earliest else "all time",
        )
        sid = client.create_job(query, earliest=earliest, latest="now")
        try:
            status = wait_for_job(
                client,
                sid,
                self._should_stop,
                QUEUED_LIMIT_SECONDS,
                sleep=self._sleep,
                clock=self._clock,
            )
            if status is None:
                logger.info("Splunk scan stopped before search %s finished", sid)
                return

            read, published, stopped = 0, 0, False
            while True:
                columns, rows = client.results(sid, offset=read)
                if not rows:
                    break
                if read == 0:
                    # Before a single record is built: see `discovery.siem.records`.
                    require_contract_columns(columns, subject)
                read += len(rows)
                records = records_from_rows(
                    rows,
                    vendor=VENDOR,
                    instance=instance,
                    query=query,
                    logger=logger,
                )
                published += len(records)
                if records:
                    yield records
                if read >= status.result_count or len(rows) < client.page_size:
                    break
                if self._should_stop():
                    stopped = True
                    break

            _report(logger, sid, status.result_count, read, published, status, stopped)
        finally:
            client.delete_job(sid)


def _report(
    logger: logging.Logger,
    sid: str,
    result_count: int,
    read: int,
    published: int,
    status: JobStatus,
    stopped: bool,
) -> None:
    """Say how complete the answer is. A partial answer must not read as a full one."""
    logger.info(
        "Splunk scan read %s of %s result row(s), %s record(s)",
        read,
        result_count,
        published,
    )
    if status.is_finalized:
        logger.warning(
            "Splunk finalized search %s before it completed (srchMaxTime or a manual "
            "stop), so its results are partial",
            sid,
        )
    if not stopped and read < result_count:
        logger.warning(
            "Splunk search %s reported %s result(s) but %s were readable; the rest "
            "were truncated by the search head",
            sid,
            result_count,
            read,
        )
    if result_count == 0:
        # Zero rows reads as a clean estate and is often not one: a role that cannot
        # read the queried index gets an empty result, not an error.
        logger.warning(
            "Splunk search %s returned no rows. If agents are expected, check that the "
            "token's role can search the indexes the query reads (srchIndexesAllowed).",
            sid,
        )


def search_text(query: Optional[str]) -> str:
    """The config's SPL as the search API accepts it.

    The API requires a search to start with `search` or a generating command's `|`;
    the search bar adds `search` silently, so a query pasted from it often lacks one.
    Only the first word is looked at -- the query is not parsed.
    """
    text = (query or "").strip()
    if not text:
        raise ValueError(
            "Splunk source config has no query. It needs SPL whose results carry "
            "external_id, name and last_seen.",
        )
    first = text.split(None, 1)[0].lower()
    if first == "search" or text.startswith("|"):
        return text
    return f"search {text}"


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> SplunkSettings:
    """The search head's address and trust from the source's fields, the token from
    its secrets. `base_url` is not a secret, so a failure can name the host."""
    base_url = (source_fields.get(BASE_URL_FIELD) or "").strip()
    missing = [k for k in (AUTH_TOKEN_FIELD,) if not credentials.get(k)]
    if not base_url:
        missing.insert(0, BASE_URL_FIELD)
    if missing:
        raise ValueError(
            f"Splunk source is missing required field(s): {', '.join(missing)}. "
            f"base_url is a source field; auth_token is a secret.",
        )
    if not base_url.lower().startswith("https://"):
        # The token travels in a header. Over http it is in cleartext, and this is the
        # only place it can be refused before it is sent.
        raise ValueError(
            f"Splunk base_url must be https, got "
            f"{base_url.split('://', 1)[0] or base_url!r}. The token travels in a "
            f"request header.",
        )

    mode = parse_tls_verification(source_fields.get(TLS_VERIFICATION_FIELD), "Splunk")

    return SplunkSettings(
        base_url=base_url,
        auth_token=str(credentials[AUTH_TOKEN_FIELD]),
        ca_certificate=(source_fields.get(CA_CERTIFICATE_FIELD) or "").strip() or None,
        tls_verification=mode,
    )


def _instance(base_url: str) -> str:
    """host:port, so two Splunk deployments behind one hostname stay distinct.

    Built from the parsed host rather than taken as the netloc, which would carry any
    `user:password@` written into the URL onto every record.
    """
    parts = urlsplit(base_url)
    host = parts.hostname or base_url
    return f"{host}:{parts.port}" if parts.port else host
