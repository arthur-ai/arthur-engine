"""Elastic Security's side of a DISCOVER_AGENTS scan.

Runs the source config's ES|QL over the scan's lookback, checks the result's columns
against the output contract, and hands the rows onward as records. What a row MEANS is
the customer's query's business: it names the columns through `STATS ... BY`, `EVAL`,
`RENAME` and `KEEP`, and nothing here maps fields.

ES|QL, NEVER QUERY DSL. Query DSL cannot name its output columns, and the contract is
checked against exactly the names the query returns, so a DSL body is refused before
anything is sent rather than left to fail at Elasticsearch's parser.

ONE CALL, SO ONE ANSWER. `_query` has no cursor: the result is everything the cluster
will return, and whether that is everything there is has to be read off the row count
(see `discovery.siem.elastic_security.client`). A capped answer is reported in the job
log, never published as though it were complete.
"""

import base64
import logging
import re
from typing import Callable, Iterator, Mapping, Optional, Sequence
from urllib.parse import urlsplit

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from discovery.siem.elastic_security.client import (
    ElasticClient,
    ElasticSettings,
    EsqlResult,
)
from discovery.siem.records import records_from_rows, require_contract_columns
from discovery.siem.tls import parse_tls_verification
from job_executors.discovery_scan import DiscoveryConfigurationError

VENDOR = "elastic_security"

ELASTICSEARCH_URL_FIELD = "elasticsearch_url"
API_KEY_FIELD = "api_key"
CA_CERTIFICATE_FIELD = "ca_certificate"
TLS_VERIFICATION_FIELD = "tls_verification"

# The cluster's row caps, at their defaults: `esql.query.result_truncation_default_size`
# without a LIMIT and `esql.query.result_truncation_max_size` with one. A cluster can
# raise them; one that has is reported as complete up to its own cap, which is the
# most these numbers can say without a privilege the key does not need otherwise.
DEFAULT_ROW_LIMIT = 1_000
MAX_ROW_LIMIT = 10_000
_DEFAULT_LIMIT_WARNING = "No limit defined, adding default limit of"

# What ES|QL names the one column of a query whose FROM matched no index.
_NO_FIELDS_COLUMN = "<no-fields>"

# A bracketed or quoted span of an Elasticsearch warning. Evaluation warnings quote the
# value that failed -- `failed to parse date field [alice@corp.com]` -- and a job log is
# not where a customer's log data should be copied to, as `discovery.siem.records`
# says of row values.
_QUOTED_SPAN = re.compile(r"\[[^\]]*\]|'[^']*'|\"[^\"]*\"")

# Records per published batch. The rows have all arrived already; this only bounds how
# much one failed publish costs.
BATCH_SIZE = 500

ClientFactory = Callable[[ElasticSettings, logging.Logger], ElasticClient]


def _default_client(settings: ElasticSettings, logger: logging.Logger) -> ElasticClient:
    return ElasticClient(settings, logger=logger)


class ElasticSecurityConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck`.

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    def __init__(self, client_factory: ClientFactory = _default_client) -> None:
        self._client_factory = client_factory
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
        query = esql_text(config.query)
        instance = _instance(settings.elasticsearch_url)
        subject = f"Source config '{config.name}' ({VENDOR})"
        client = self._client_factory(settings, logger)

        logger.info(
            "Elastic scan starting against %s, lookback %s",
            instance,
            f"{lookback_hours}h" if lookback_hours > 0 else "all time",
        )
        # The query is a single call bounded by its own timeout, so the one safe point
        # to honour a stop is before it is sent.
        if self._should_stop():
            logger.info("Elastic scan stopped before its query was sent")
            return

        result = client.query(query, lookback_hours if lookback_hours > 0 else None)
        for warning in result.warnings:
            if not warning.startswith(_DEFAULT_LIMIT_WARNING):
                logger.warning("Elasticsearch warned: %s", _redacted(warning))

        if not result.rows and _NO_FIELDS_COLUMN in result.columns:
            logger.warning(
                "Elastic query matched no index, so there is nothing to read. Check "
                "the index pattern in its FROM, and that the API key has 'read' on it.",
            )
            return

        # Before a single record is built: see `discovery.siem.records`.
        require_contract_columns(result.columns, subject)
        records = records_from_rows(
            result.rows,
            vendor=VENDOR,
            instance=instance,
            query=query,
            logger=logger,
        )
        # Reported before the first batch is handed over, so a publish that fails part
        # way cannot leave a capped or partial answer unannounced.
        _report(logger, result, len(records), lookback_hours > 0)
        for start in range(0, len(records), BATCH_SIZE):
            yield records[start : start + BATCH_SIZE]


def _report(
    logger: logging.Logger,
    result: EsqlResult,
    records: int,
    lookback_applied: bool,
) -> None:
    """Say how complete the answer is. A partial answer must not read as a full one."""
    rows = len(result.rows)
    logger.info("Elastic query returned %s row(s), %s record(s)", rows, records)

    # TODO(UP-4990): report a capped result on the scan outcome, not only the job log,
    # once the framework has a way for a connector to say so. Splunk and Google SecOps
    # need the same.
    default_limited = any(w.startswith(_DEFAULT_LIMIT_WARNING) for w in result.warnings)
    if default_limited and rows >= DEFAULT_ROW_LIMIT:
        logger.warning(
            "Elastic query has no LIMIT and returned %s rows, Elasticsearch's default "
            "cap, so rows past it were probably not read. Aggregate to one row per agent (STATS ... "
            "BY) and end the query with LIMIT %s.",
            rows,
            MAX_ROW_LIMIT,
        )
    elif rows >= MAX_ROW_LIMIT:
        logger.warning(
            "Elastic query returned %s rows, Elasticsearch's maximum for one query, so "
            "the result is probably incomplete. Aggregate to fewer rows (STATS ... BY).",
            rows,
        )
    if result.is_partial:
        logger.warning(
            "Elasticsearch marked the result partial: some shards failed to answer, so "
            "rows they hold are missing.",
        )
    if rows == 0:
        logger.warning(
            "Elastic query returned no rows. If agents are expected, check the index "
            "pattern, that the API key has 'read' on those indices%s.",
            (
                ", and that the indices keep their event time in @timestamp, which the "
                "lookback filters on"
                if lookback_applied
                else ""
            ),
        )


def _redacted(warning: str) -> str:
    """An Elasticsearch warning with the values it quotes taken out."""
    return _QUOTED_SPAN.sub("[...]", warning)


def esql_text(query: Optional[str]) -> str:
    """The config's query, refused when it is not ES|QL.

    Only the first character is looked at -- the query is not parsed. ES|QL starts with
    a source command (`FROM`, `ROW`, `SHOW`, ...); a Query DSL body is a JSON object.
    """
    text = (query or "").strip()
    if not text:
        raise DiscoveryConfigurationError(
            "Elastic source config has no query. It needs ES|QL whose results carry "
            "external_id, name and last_seen.",
        )
    if text.startswith("{"):
        raise DiscoveryConfigurationError(
            "Elastic source config's query is Query DSL. Elastic sources take ES|QL "
            "(Elasticsearch 8.14 or later), because only ES|QL can name its output "
            "columns -- with STATS ... BY, EVAL, RENAME and KEEP -- and the result must "
            "carry external_id, name and last_seen. Example: FROM logs-* | WHERE "
            'destination.domain == "api.openai.com" | STATS last_seen = MAX(@timestamp) '
            "BY external_id = host.name | EVAL name = external_id | LIMIT 10000",
        )
    return text


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> ElasticSettings:
    """The cluster's address and trust from the source's fields, the key from its
    secrets. `elasticsearch_url` is not a secret, so a failure can name the host."""
    url = (source_fields.get(ELASTICSEARCH_URL_FIELD) or "").strip()
    api_key = (credentials.get(API_KEY_FIELD) or "").strip()
    missing = [
        k
        for k, v in ((ELASTICSEARCH_URL_FIELD, url), (API_KEY_FIELD, api_key))
        if not v
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"Elastic source is missing required field(s): {', '.join(missing)}. "
            f"elasticsearch_url is a source field; api_key is a secret.",
        )
    if not url.lower().startswith("https://"):
        # The key travels in a header. Over http it is in cleartext, and this is the
        # only place it can be refused before it is sent.
        raise DiscoveryConfigurationError(
            f"Elastic elasticsearch_url must be https, got "
            f"{url.split('://', 1)[0] or url!r}. The API key travels in a request header.",
        )
    # Parsed here, where a bad value is the source's to fix, rather than when the
    # request or the record's address first reads it. The problem is raised after
    # the except block, so no ValueError rides on __context__ for Test Connection to
    # read as the vendor's.
    problem: Optional[str] = None
    try:
        parts = urlsplit(url)
        parts.port
        if not parts.hostname:
            problem = "it has no host"
    except ValueError as exc:
        problem = str(exc)
    if problem is not None:
        raise DiscoveryConfigurationError(
            f"Elastic elasticsearch_url is not a valid URL ({problem}). Expected "
            f"https://host or https://host:port.",
        )

    return ElasticSettings(
        elasticsearch_url=url,
        api_key=_encoded(api_key),
        ca_certificate=(source_fields.get(CA_CERTIFICATE_FIELD) or "").strip() or None,
        tls_verification=parse_tls_verification(
            source_fields.get(TLS_VERIFICATION_FIELD), "Elastic"
        ),
    )


def _encoded(api_key: str) -> str:
    """The key as the ApiKey header takes it.

    The field asks for the `encoded` value, base64 of `id:api_key`. A key pasted as
    `id:api_key` is encoded here rather than refused; base64 never contains a colon,
    so the two cannot be confused.
    """
    if ":" in api_key:
        return base64.b64encode(api_key.encode()).decode()
    return api_key


def _instance(url: str) -> str:
    """The cluster as one stable string: host, a port other than 443, and any path.

    The same cluster written with and without its default port is one instance, and
    two clusters routed by path behind one gateway (`https://gw.corp/es-prod`,
    `/es-dev`) are two. An IPv6 host keeps its brackets so the port stays readable.
    Built from the parsed host rather than taken as the netloc, which would carry any
    `user:password@` written into the URL onto every record.
    """
    parts = urlsplit(url)
    host = (parts.hostname or url).lower()
    if ":" in host:
        host = f"[{host}]"
    if parts.port and parts.port != 443:
        host = f"{host}:{parts.port}"
    path = parts.path.rstrip("/")
    return f"{host}{path}"
