"""Amazon CloudWatch Logs' side of a DISCOVER_AGENTS scan.

Reads every event of the source's log groups in the scan's lookback with
`FilterLogEvents`, pulls a source and a destination out of each line with the source's
extractor (a preset `log_format`, or `custom` and its own regex), keeps the lines whose
destination serves model inference (`discovery.network.hosts` plus the source's own
hosts and CIDRs), and reports one record per internal source
(`discovery.network.records`).

THERE IS NO QUERY. The catalog's query language is `none`: the extractor is a field of
the source, because it describes the log group, which every config of the source reads.
A config's query is ignored, and the scan says so.

BOUNDED. At most `MAX_EVENTS` events are read per scan, across its log groups, and a
capped scan says so before its first batch. The lines are matched in the engine, so
the extractor's per-line timeout and length cap are what bound a pathological pattern.
A stopped scan (Test Connection's deadline) reports what it read so far: every record
is evidence on its own, whatever was left unread.
"""

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from discovery.network.cloudwatch_logs.client import (
    CloudWatchLogsClient,
    CloudWatchLogsSettings,
)
from discovery.network.extractor import PRESETS, Extractor, pattern_problem
from discovery.network.hosts import (
    MAX_EXTRA_DESTINATIONS,
    DestinationMatcher,
    destination_problem,
)
from discovery.network.records import TrafficSources
from job_executors.discovery_scan import DiscoveryConfigurationError

VENDOR = "aws_cloudwatch_logs"

REGION_FIELD = "region"
LOG_GROUP_NAMES_FIELD = "log_group_names"
LOG_FORMAT_FIELD = "log_format"
EXTRACTION_REGEX_FIELD = "extraction_regex"
ACCESS_KEY_ID_FIELD = "access_key_id"
SECRET_ACCESS_KEY_FIELD = "secret_access_key"
ROLE_ARN_FIELD = "role_arn"
EXTERNAL_ID_FIELD = "external_id"
EXTRA_INFERENCE_HOSTS_FIELD = "extra_inference_hosts"

CUSTOM_LOG_FORMAT = "custom"

# Opt-in for the engine's own AWS credentials (instance profile, IRSA, environment)
# when a source has no access key. Off unless set to a true value, so a keyless source
# fails naming its fields rather than scanning as whatever the engine runs as.
ALLOW_DEFAULT_CREDENTIALS_ENV_VAR = (
    "ARTHUR_ENGINE_AWS_CLOUDWATCH_LOGS_ALLOW_DEFAULT_CREDENTIALS"
)

MAX_LOG_GROUPS = 20
MAX_EVENTS = 1_000_000
BATCH_SIZE = 500

_REGION = re.compile(r"^[a-z]{2}(?:-[a-z]+)+-\d{1,2}$")
_ROLE_ARN = re.compile(r"^arn:aws[a-z-]*:iam::\d{12}:role/[\w+=,.@/-]+$")
_LOG_GROUP_NAME = re.compile(r"^[\w#./-]{1,512}$")
_LOG_GROUP_ARN = re.compile(
    r"^arn:aws[a-z-]*:logs:[a-z0-9-]+:\d{12}:log-group:[\w#./-]{1,512}$"
)

ClientFactory = Callable[[CloudWatchLogsSettings, logging.Logger], CloudWatchLogsClient]


class CloudWatchLogsConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck` (structurally; the Protocols are not imported).

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SECRET_ACCESS_KEY_FIELD})

    def __init__(
        self,
        client_factory: ClientFactory = CloudWatchLogsClient,
        now: Callable[[], float] = time.time,
        max_events: int = MAX_EVENTS,
    ) -> None:
        self._client_factory = client_factory
        self._now = now
        self._max_events = max_events
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
        """`logger` is the JOB's, so what this reports reaches the Platform job log.

        A lookback of 0 reads everything the log groups still retain, up to the cap.
        """
        settings = settings_from(credentials, source_fields)
        extractor = Extractor(extraction_pattern_from(source_fields))
        matcher = DestinationMatcher(extra_destinations_from(source_fields))
        if (config.query or "").strip():
            logger.warning(
                "CloudWatch Logs sources have no query; the source config's query is "
                "ignored. The source's log_format reads the lines.",
            )

        end_ms = int(self._now() * 1000)
        start_ms = end_ms - lookback_hours * 3_600_000 if lookback_hours > 0 else 0
        logger.info(
            "CloudWatch Logs scan starting against %s log group(s) in %s, lookback %s, "
            "%s known inference host(s), %s extra range(s)",
            len(settings.log_groups),
            settings.region,
            f"{lookback_hours}h" if lookback_hours > 0 else "all retained logs",
            len(matcher.hosts),
            len(matcher.networks),
        )
        if self._should_stop():
            logger.info("CloudWatch Logs scan stopped before reading any log group")
            return

        client = self._client_factory(settings, logger)
        sources = TrafficSources(default_instance=settings.region)
        read = matched = 0
        capped = False
        for group in settings.log_groups:
            for page in client.events(group, start_ms, end_ms, self._should_stop):
                for event in page[: self._max_events - read]:
                    read += 1
                    line = extractor.extract(event.message)
                    if line is None:
                        continue
                    destination = matcher.match(line.dest)
                    if destination is None:
                        continue
                    matched += 1
                    seen_at = datetime.fromtimestamp(
                        event.timestamp_ms / 1000, tz=timezone.utc
                    )
                    sources.add(line, destination, seen_at)
                if read >= self._max_events:
                    capped = True
                    break
            if capped or self._should_stop():
                break

        records = sources.records(VENDOR)
        # Reported before the first batch is handed over, so a publish that fails part
        # way cannot leave a capped answer unannounced.
        self._report(logger, extractor, sources, read, matched, capped)
        for offset in range(0, len(records), BATCH_SIZE):
            yield records[offset : offset + BATCH_SIZE]

    def _report(
        self,
        logger: logging.Logger,
        extractor: Extractor,
        sources: TrafficSources,
        read: int,
        matched: int,
        capped: bool,
    ) -> None:
        """How complete the answer is and what it found, in counts and provider names
        only: never a line, an address or a host from the logs."""
        counts = extractor.counts
        logger.info(
            "CloudWatch Logs scan read %s event(s): %s extracted, %s did not match the "
            "extractor, %s calls to inference hosts from %s source(s)",
            read,
            counts.extracted,
            counts.unmatched,
            matched,
            len(sources),
        )
        for provider, count in sorted(sources.calls_by_provider().items()):
            logger.info("CloudWatch Logs: %s source(s) called %s", count, provider)
        if counts.timed_out or counts.too_long:
            logger.warning(
                "CloudWatch Logs: %s line(s) skipped because the extractor ran past "
                "its per-line time limit and %s because they were too long to read. "
                "Simplify extraction_regex (avoid nested quantifiers such as (a+)+).",
                counts.timed_out,
                counts.too_long,
            )
        if read and not counts.extracted:
            logger.warning(
                "CloudWatch Logs: no line matched the extractor. Check that log_format "
                "or extraction_regex fits what the log groups hold.",
            )
        if capped:
            logger.warning(
                "CloudWatch Logs scan stopped at its %s-event cap, so later events "
                "were not read. Shorten the lookback window or split the log groups "
                "across sources.",
                self._max_events,
            )
        elif self._should_stop():
            logger.info(
                "CloudWatch Logs scan stopped early after %s event(s); records cover "
                "what was read",
                read,
            )
        if read == 0:
            logger.warning(
                "CloudWatch Logs scan read no events. Check that the log groups "
                "receive logs and that the lookback window covers them.",
            )


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> CloudWatchLogsSettings:
    """The region and log groups from the source's fields, the secret key from its
    credentials."""
    region = (source_fields.get(REGION_FIELD) or "").strip().lower()
    log_groups = _list(source_fields.get(LOG_GROUP_NAMES_FIELD))
    missing = [
        name
        for name, value in ((REGION_FIELD, region), (LOG_GROUP_NAMES_FIELD, log_groups))
        if not value
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs source is missing required field(s): "
            f"{', '.join(missing)}.",
        )
    if not _REGION.match(region):
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {REGION_FIELD} is not an AWS region code. Expected e.g. "
            f"us-east-1.",
        )
    if len(log_groups) > MAX_LOG_GROUPS:
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {LOG_GROUP_NAMES_FIELD} names {len(log_groups)} log "
            f"groups; a source reads at most {MAX_LOG_GROUPS}. Split them across "
            f"sources.",
        )
    bad = [
        i + 1
        for i, group in enumerate(log_groups)
        if not (_LOG_GROUP_NAME.match(group) or _LOG_GROUP_ARN.match(group))
    ]
    if bad:
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {LOG_GROUP_NAMES_FIELD} entry {bad[0]} is neither a log "
            f"group name nor a log group ARN (without the trailing :*).",
        )

    access_key_id = (source_fields.get(ACCESS_KEY_ID_FIELD) or "").strip() or None
    secret = (credentials.get(SECRET_ACCESS_KEY_FIELD) or "").strip() or None
    if bool(access_key_id) != bool(secret):
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs source has only one of {ACCESS_KEY_ID_FIELD} and "
            f"{SECRET_ACCESS_KEY_FIELD}. Set both, or neither to use the engine's own "
            f"credentials.",
        )
    if access_key_id is None and not _default_credentials_allowed():
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs source has no {ACCESS_KEY_ID_FIELD} and "
            f"{SECRET_ACCESS_KEY_FIELD}. Set them on the source, or set "
            f"{ALLOW_DEFAULT_CREDENTIALS_ENV_VAR}=true on this engine to use its own "
            f"AWS credentials.",
        )
    role_arn = (source_fields.get(ROLE_ARN_FIELD) or "").strip() or None
    external_id = (source_fields.get(EXTERNAL_ID_FIELD) or "").strip() or None
    if role_arn and not _ROLE_ARN.match(role_arn):
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {ROLE_ARN_FIELD} is not an IAM role ARN. Expected "
            f"arn:aws:iam::<account>:role/<name>.",
        )
    if external_id and not role_arn:
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {EXTERNAL_ID_FIELD} is set without {ROLE_ARN_FIELD}; an "
            f"external ID is only sent when assuming a role.",
        )
    return CloudWatchLogsSettings(
        region=region,
        log_groups=tuple(dict.fromkeys(log_groups)),
        access_key_id=access_key_id,
        secret_access_key=secret,
        role_arn=role_arn,
        external_id=external_id,
    )


def extraction_pattern_from(source_fields: Mapping[str, str]) -> str:
    """The regex the source's lines are read with: its preset's, or its own for
    `custom`.

    One required mode rather than two optional alternatives, because the Platform's
    source form cannot clear a saved field: switching between a preset and a regex
    has to be a change of `log_format`. `extraction_regex` is read only for `custom`.
    """
    log_format = (source_fields.get(LOG_FORMAT_FIELD) or "").strip()
    if not log_format:
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs source is missing required field(s): {LOG_FORMAT_FIELD}.",
        )
    if log_format != CUSTOM_LOG_FORMAT:
        preset = PRESETS.get(log_format)
        if preset is None:
            raise DiscoveryConfigurationError(
                f"CloudWatch Logs {LOG_FORMAT_FIELD} must be one of "
                f"{', '.join(sorted(PRESETS) + [CUSTOM_LOG_FORMAT])}.",
            )
        return preset
    pattern = source_fields.get(EXTRACTION_REGEX_FIELD) or ""
    if not pattern.strip():
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {LOG_FORMAT_FIELD} {CUSTOM_LOG_FORMAT} needs "
            f"{EXTRACTION_REGEX_FIELD}: a regex with named groups src and dest.",
        )
    problem = pattern_problem(pattern)
    if problem is not None:
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {EXTRACTION_REGEX_FIELD} {problem}.",
        )
    return pattern


def extra_destinations_from(source_fields: Mapping[str, str]) -> tuple[str, ...]:
    """The source's own inference hosts and ranges, lowercased, refused when one is
    neither a host pattern nor an IP address or CIDR."""
    entries = [
        e.lower().rstrip(".")
        for e in _list(source_fields.get(EXTRA_INFERENCE_HOSTS_FIELD))
    ]
    if len(entries) > MAX_EXTRA_DESTINATIONS:
        raise DiscoveryConfigurationError(
            f"CloudWatch Logs {EXTRA_INFERENCE_HOSTS_FIELD} lists {len(entries)} "
            f"entries; at most {MAX_EXTRA_DESTINATIONS} are read.",
        )
    for i, entry in enumerate(entries):
        problem = destination_problem(entry)
        if problem:
            raise DiscoveryConfigurationError(
                f"CloudWatch Logs {EXTRA_INFERENCE_HOSTS_FIELD} entry {i + 1} "
                f"{problem}.",
            )
    return tuple(dict.fromkeys(entries))


def _default_credentials_allowed() -> bool:
    value = os.getenv(ALLOW_DEFAULT_CREDENTIALS_ENV_VAR, "")
    return value.strip().lower() in {"1", "true", "yes"}


def _list(raw: Optional[str]) -> list[str]:
    return [part.strip() for part in re.split(r"[,\n]", raw or "") if part.strip()]
