"""GCP network logs' side of a DISCOVER_AGENTS scan (`gcp_network`).

Reads one project's Cloud DNS query logs and VPC flow logs from Cloud Logging and
reports one network record per workload seen calling a host that serves model
inference: a Compute Engine VM from its own DNS lookups, a Cloud Run job or service
from its flow records labelled by the DNS answers. `discovery.network.gcp_logging.records`
says how each is named and why a GKE pod cannot be.

THE LOGS MUST BE ON. Cloud DNS logging is a DNS server policy per VPC network, and flow
logs a setting per subnet; neither is on by default. Under Shared VPC both are written
to the host project, so that is the project a source names.

CREDENTIALS. A service account key, as for the other Google sources, needs
`roles/logging.viewer`; `roles/run.viewer` additionally lets a Cloud Run job execution
be folded into its job. A keyless source uses Application Default Credentials only when
the engine opts in with `ALLOW_ADC_ENV_VAR`.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import (
    Any,
    Callable,
    ClassVar,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
)

import google.auth
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from google.auth.credentials import Credentials
from pydantic import BaseModel

from discovery.gcp_credentials import (
    SERVICE_ACCOUNT_KEY_FIELD,
    service_account_credentials,
)
from discovery.network.cloudwatch_logs.connector import extra_destinations_from
from discovery.network.gcp_logging.client import (
    LoggingReadError,
    dns_filter,
    list_run_jobs,
    read_entries,
    serverless_flow_filter,
    session_for,
)
from discovery.network.gcp_logging.records import NetworkFold
from discovery.network.hosts import DestinationMatcher
from job_executors.discovery_scan import DiscoveryConfigurationError

VENDOR = "gcp_network"

PROJECT_ID_FIELD = "project_id"
EXTRA_INFERENCE_HOSTS_FIELD = "extra_inference_hosts"

ALLOW_ADC_ENV_VAR = "ARTHUR_ENGINE_GCP_NETWORK_ALLOW_ADC"
CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

# A lookback of zero reads this far back rather than the whole retention.
DEFAULT_LOOKBACK = timedelta(days=1)
# Entries read per log per scan at most; a capped scan says so.
MAX_ENTRIES = 200_000
BATCH_SIZE = 100


class GcpNetworkSettings(BaseModel):
    project_id: str
    extra_inference_hosts: tuple[str, ...] = ()


class Logs:
    """What a scan reads. A seam so tests can hand in captured entries."""

    def __init__(self, credentials: Optional[Credentials]) -> None:
        if credentials is None:
            credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
        self._session = session_for(credentials)

    def entries(self, project_id: str, log_filter: str) -> Iterable[dict[str, Any]]:
        return read_entries(self._session, project_id, log_filter)

    def run_jobs(self, project_id: str, region: str) -> set[str]:
        return list_run_jobs(self._session, project_id, region)


LogsFactory = Callable[[Optional[Credentials]], Logs]


class GcpNetworkConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`."""

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SERVICE_ACCOUNT_KEY_FIELD})

    def __init__(
        self,
        logs: LogsFactory = Logs,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._logs = logs
        self._clock = clock

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        settings = settings_from(source_fields)
        google_credentials = service_account_credentials(
            credentials,
            source="GCP network logs source",
            allow_adc_env_var=ALLOW_ADC_ENV_VAR,
            scopes=[CLOUD_PLATFORM_SCOPE],
        )
        now = self._clock()
        since = now - (
            timedelta(hours=lookback_hours) if lookback_hours > 0 else DEFAULT_LOOKBACK
        )
        logs = self._logs(google_credentials)
        project = settings.project_id
        logger.info(
            "GCP network logs scan starting against project %s since %s",
            project,
            since.isoformat(),
        )

        def run_jobs(region: str) -> set[str]:
            try:
                return logs.run_jobs(project, region)
            except LoggingReadError as e:
                logger.warning(
                    "GCP network logs: Cloud Run jobs in %s not listed (HTTP %s); job "
                    "executions there are reported by execution name. roles/run.viewer "
                    "lets them be folded into their job.",
                    region,
                    e.status_code,
                )
                return set()

        fold = NetworkFold(DestinationMatcher(settings.extra_inference_hosts), run_jobs)
        capped = _read(logs, project, dns_filter(project, since), fold.lookup)
        capped |= _read(
            logs, project, serverless_flow_filter(project, since), fold.flow
        )

        records = fold.records(VENDOR)
        counts = fold.counts
        logger.info(
            "GCP network logs for %s: %s DNS lookup(s), %s to inference hosts (%s from "
            "sources DNS does not name); %s serverless flow(s), %s to inference "
            "addresses, %s to addresses shared with other hosts and skipped; %s "
            "record(s)",
            project,
            counts.lookups,
            counts.inference_lookups,
            counts.unplaced_lookups,
            counts.flows,
            counts.inference_flows,
            counts.ambiguous_flows,
            len(records),
        )
        if counts.lookups == 0:
            logger.warning(
                "GCP network logs for %s: no Cloud DNS lookups in the window. Cloud DNS "
                "logging is a DNS server policy on the VPC network; under Shared VPC "
                "the logs are in the host project.",
                project,
            )
        if capped:
            logger.warning(
                "GCP network logs for %s: stopped at %s entries in a log; shorten the "
                "lookback to read the rest",
                project,
                MAX_ENTRIES,
            )
        for offset in range(0, len(records), BATCH_SIZE):
            yield records[offset : offset + BATCH_SIZE]


def _read(
    logs: Logs, project: str, log_filter: str, each: Callable[[dict[str, Any]], None]
) -> bool:
    """Feeds every entry to `each`; True when it stopped at MAX_ENTRIES."""
    for count, entry in enumerate(logs.entries(project, log_filter)):
        if count >= MAX_ENTRIES:
            return True
        each(entry)
    return False


def settings_from(source_fields: Mapping[str, str]) -> GcpNetworkSettings:
    project_id = (source_fields.get(PROJECT_ID_FIELD) or "").strip()
    if not project_id:
        raise DiscoveryConfigurationError(
            f"GCP network logs source is missing required field '{PROJECT_ID_FIELD}': "
            "the project whose Cloud DNS and flow logs are read (the host project "
            "under Shared VPC).",
        )
    return GcpNetworkSettings(
        project_id=project_id,
        # Same rules (and field name) as the AWS network source.
        extra_inference_hosts=extra_destinations_from(source_fields),
    )
