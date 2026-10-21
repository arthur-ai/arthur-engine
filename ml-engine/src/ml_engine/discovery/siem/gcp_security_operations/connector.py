"""Google Security Operations' side of a DISCOVER_AGENTS scan.

Runs the source config's YARA-L statistics query over the scan's lookback, checks the
result's columns against the output contract, and hands the rows onward as records.
What a row MEANS is the customer's query's business: its `match:` and `outcome:`
variables name the columns (`$external_id`, `$name`, `$last_seen`, ...), and nothing
here maps fields.

YARA-L, NEVER A JSON BODY. Only a statistics query names its output columns, and the
contract is checked against exactly the names it returns, so a config in another
language, or a JSON request pasted in its place, is refused before anything is sent.

ONE CALL, SO ONE ANSWER. `dashboardQueries:execute` has no page token: the result is
everything the instance will return, and whether that is everything there is, Google
says in the answer's runtime errors (see `discovery.siem.gcp_security_operations.
client`). A capped answer is reported in the job log, never published as though it
were complete.

THE WINDOW IS GOOGLE'S TO BOUND. Search and dashboard queries read at most the last 90
days of events, so a lookback of "all time" (zero) or anything longer is sent as 90
days, and the job log says so rather than Google refusing the window.

NO TLS SETTINGS. Unlike a self-hosted SIEM, every instance is behind a Google API host
with a publicly trusted certificate, so there is no CA to add and verification is never
turned off for a connection carrying a Google token -- as for the Vertex AI and Compute
Engine connectors.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from discovery.gcp_credentials import (
    SERVICE_ACCOUNT_KEY_FIELD,
    service_account_credentials,
)
from discovery.siem.gcp_security_operations.client import (
    CHRONICLE_READONLY_SCOPE,
    GcpSecurityOperationsClient,
    GcpSecurityOperationsSettings,
    QueryResult,
)
from discovery.siem.records import records_from_rows, require_contract_columns
from job_executors.discovery_scan import DiscoveryConfigurationError

# The wire value. Identical to arthur-client's DiscoverySourceVendor member.
VENDOR = "gcp_security_operations"

# The Platform catalog's query_language for this vendor. Newer than the pinned
# arthur-client's DiscoveryQueryLanguage, which is why standalone mode accepts it by
# name (`standalone.discovery_config`).
QUERY_LANGUAGE = "yara_l"

# Field names. Identical to the Platform catalog's field names, in its order; the key
# is `SERVICE_ACCOUNT_KEY_FIELD`, shared with every Google connector.
PROJECT_ID_FIELD = "project_id"
LOCATION_FIELD = "location"
INSTANCE_ID_FIELD = "instance_id"

# Opt-in for Application Default Credentials when a source has no key, as Vertex AI and
# Compute Engine have. Off unless set to a true value; see `discovery.gcp_credentials`.
ALLOW_ADC_ENV_VAR = "ARTHUR_ENGINE_GCP_SECURITY_OPERATIONS_ALLOW_ADC"

# How far back a search or dashboard query can read, per Google's service limits.
MAX_LOOKBACK_HOURS = 90 * 24

# Records per published batch. The rows have all arrived already; this only bounds how
# much one failed publish costs.
BATCH_SIZE = 500

# A Google Security Operations region as it appears in its host: `us`, `eu`, `europe`,
# `europe-west2`, `northamerica-northeast2`. Checked strictly because it becomes part
# of the host the Google token is sent to: nothing else may get through.
_LOCATION = re.compile(r"^[a-z]+(?:-[a-z]+[0-9]+)?$")

# A project ID (optionally domain-scoped, `example.com:my-project`) or a project
# number. Checked because it is a path segment.
_PROJECT_ID = re.compile(
    r"^(?:(?:[a-z0-9.-]+:)?[a-z][a-z0-9-]{4,28}[a-z0-9]|[0-9]{1,30})$",
)

# The instance's customer ID, a UUID. Held to one path segment of letters, digits and
# dashes rather than to the UUID form, which Google does not promise.
_INSTANCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,127}$")

ClientFactory = Callable[
    [GcpSecurityOperationsSettings, logging.Logger],
    GcpSecurityOperationsClient,
]


def _default_client(
    settings: GcpSecurityOperationsSettings,
    logger: logging.Logger,
) -> GcpSecurityOperationsClient:
    return GcpSecurityOperationsClient(settings, logger=logger)


class GcpSecurityOperationsConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck`.

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    # Must equal the set of fields the Platform catalog marks is_sensitive.
    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SERVICE_ACCOUNT_KEY_FIELD})

    def __init__(
        self,
        client_factory: ClientFactory = _default_client,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._client_factory = client_factory
        self._clock = clock
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before the query is sent and before each retry of it."""
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
        query = query_text(config)
        settings = settings_from(credentials, source_fields)
        instance = _instance(settings)
        subject = f"Source config '{config.name}' ({VENDOR})"
        client = self._client_factory(settings, logger)

        hours = _window_hours(lookback_hours, logger)
        end = self._clock().astimezone(timezone.utc)
        start = end - timedelta(hours=hours)
        logger.info(
            "Google Security Operations scan starting against %s, window %s to %s",
            instance,
            _rfc3339(start),
            _rfc3339(end),
        )
        # The query is a single call bounded by its own timeout, so the safe points to
        # honour a stop are before it is sent and before any retry.
        if self._should_stop():
            logger.info(
                "Google Security Operations scan stopped before its query was sent",
            )
            return

        result = client.query(query, _rfc3339(start), _rfc3339(end), self._should_stop)

        if not result.columns and not result.rows:
            # No columns at all: Google leaves `results` out when a query matched
            # nothing, so there are no names to check against the contract.
            _report(logger, result, 0)
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
        _report(logger, result, len(records))
        for start_at in range(0, len(records), BATCH_SIZE):
            yield records[start_at : start_at + BATCH_SIZE]


def _window_hours(lookback_hours: int, logger: logging.Logger) -> int:
    """The lookback Google will serve: the config's, or 90 days when it asked for all
    time or for more than that."""
    if 0 < lookback_hours <= MAX_LOOKBACK_HOURS:
        return lookback_hours
    logger.warning(
        "Google Security Operations reads at most the last %s days of events, so the "
        "scan's window is %s days rather than %s.",
        MAX_LOOKBACK_HOURS // 24,
        MAX_LOOKBACK_HOURS // 24,
        "all time" if lookback_hours <= 0 else f"{lookback_hours}h",
    )
    return MAX_LOOKBACK_HOURS


def _rfc3339(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _report(logger: logging.Logger, result: QueryResult, records: int) -> None:
    """Say how complete the answer is. A partial answer must not read as a full one."""
    rows = len(result.rows)
    logger.info(
        "Google Security Operations query returned %s row(s), %s record(s)",
        rows,
        records,
    )
    # In the job log only, as for Elastic: the scan outcome has no field for a capped
    # result yet.
    for notice in result.notices:
        if notice.is_row_limit:
            logger.warning(
                "Google Security Operations stopped the query at its row limit%s "
                "(%s), so rows past it were not read. %s",
                f" of {notice.row_limit}" if notice.row_limit is not None else "",
                notice.reason,
                (
                    "Add a limit: section (at most 10000) or aggregate to fewer rows."
                    if notice.reason != "ROW_LIMIT_EXCEEDED"
                    else "Aggregate to fewer rows: match on fewer variables or filter "
                    "the events more narrowly."
                ),
            )
        else:
            logger.warning(
                "Google Security Operations reported a %s runtime error while running "
                "the query%s, so the result may be incomplete.",
                notice.severity,
                f": {notice.title}" if notice.title else "",
            )
    for column, count in sorted(result.unsupported_values.items()):
        logger.warning(
            "Google Security Operations returned %s value(s) in column %s of a type no "
            "record field holds (bytes, a date or an embedded message); they were read "
            "as empty.",
            count,
            column,
        )
    if rows == 0:
        logger.warning(
            "Google Security Operations query returned no rows. If agents are "
            "expected, check that the events it reads fall within the window, and that "
            "the service account's data access scopes, if the instance uses them, "
            "cover them.",
        )


def query_text(config: DiscoverySourceConfigSpec) -> str:
    """The config's query, refused when it is empty or plainly not YARA-L.

    Only the language the config declares and the first character are looked at -- the
    query is not parsed. A YARA-L search starts with an event filter or a placeholder
    (`metadata.event_type = ...`, `$host = ...`); a JSON request body is an object.
    """
    language = str(getattr(config, "query_language", "") or "").strip().lower()
    if language != QUERY_LANGUAGE:
        raise DiscoveryConfigurationError(
            f"Google Security Operations source config's query_language must be "
            f"{QUERY_LANGUAGE}: the source runs YARA-L statistics queries.",
        )
    text = (config.query or "").strip()
    if not text:
        raise DiscoveryConfigurationError(
            "Google Security Operations source config has no query. It needs a YARA-L "
            "statistics query whose match: and outcome: variables are named "
            "external_id, name and last_seen.",
        )
    if text.startswith("{"):
        raise DiscoveryConfigurationError(
            "Google Security Operations source config's query is a JSON body. These "
            "sources take the YARA-L text alone, as the search page takes it, with "
            "match: and outcome: variables named after the output columns (external_id, "
            "name and last_seen); the lookback is applied by the engine.",
        )
    return text


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> GcpSecurityOperationsSettings:
    """Which instance from the source's fields, the identity from its credentials.

    The fields are not secrets, so a failure names the field -- but not its value,
    which the job log would then carry for whatever was pasted there.
    """
    project_id = (source_fields.get(PROJECT_ID_FIELD) or "").strip()
    location = (source_fields.get(LOCATION_FIELD) or "").strip().lower()
    instance_id = (source_fields.get(INSTANCE_ID_FIELD) or "").strip()
    missing = [
        k
        for k, v in (
            (PROJECT_ID_FIELD, project_id),
            (LOCATION_FIELD, location),
            (INSTANCE_ID_FIELD, instance_id),
        )
        if not v
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"Google Security Operations source is missing required field(s): "
            f"{', '.join(missing)}.",
        )
    if not _LOCATION.match(location):
        raise DiscoveryConfigurationError(
            f"Google Security Operations {LOCATION_FIELD} must be the instance's region "
            f"alone, such as us, eu or europe-west2 -- not a URL or a host. The engine "
            f"builds the API host from it.",
        )
    if not _PROJECT_ID.match(project_id):
        raise DiscoveryConfigurationError(
            f"Google Security Operations {PROJECT_ID_FIELD} must be the ID or number of "
            f"the Google Cloud project the instance is bound to.",
        )
    if not _INSTANCE_ID.match(instance_id):
        raise DiscoveryConfigurationError(
            f"Google Security Operations {INSTANCE_ID_FIELD} must be the instance's "
            f"customer ID (a UUID, from SIEM Settings > Profile).",
        )
    return GcpSecurityOperationsSettings(
        project_id=project_id,
        location=location,
        instance_id=instance_id,
        credentials=service_account_credentials(
            credentials,
            source="Google Security Operations source",
            allow_adc_env_var=ALLOW_ADC_ENV_VAR,
            scopes=[CHRONICLE_READONLY_SCOPE],
        ),
    )


def _instance(settings: GcpSecurityOperationsSettings) -> str:
    """The instance as one stable string: its resource name,
    `projects/<project>/locations/<location>/instances/<customer id>`.

    Not the API host. Every instance in a region shares `<location>-chronicle.
    googleapis.com`, and the Platform tells one source's records from another's by
    vendor and instance alone, so the host would make two instances one -- as the
    Sentinel row of `SourceAddress` names the workspace rather than Azure's host.
    Lower-cased: the customer ID is a UUID, which Google prints either way.
    """
    return settings.parent.lower()
