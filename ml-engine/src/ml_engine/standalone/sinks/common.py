"""What every sink target shares: the events it is handed and the API it implements.

EVERY EVENT IS SELF-DESCRIBING. A destination indexes events one at a time, so each
carries its type, a schema version, when it was observed and which source and config
produced it, alongside the record or outcome itself. The two builders below are the
whole event contract; a sink target only frames and delivers what it is given.
"""

from datetime import datetime, timezone
from typing import Any, Optional, Protocol, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discovery_scan import DiscoveryScanOutcome

# Bumped when a field changes meaning or goes away; adding one does not.
EVENT_SCHEMA_VERSION = 1
DISCOVERED_AGENT_EVENT = "arthur.discovery.agent"
SCAN_OUTCOME_EVENT = "arthur.discovery.scan_outcome"

Event = dict[str, Any]


class SinkDeliveryError(Exception):
    """Events the destination did not take. The message carries no destination secret.

    A sink's error becomes the scan's, which is logged and sent on as its outcome event,
    and the scan loop scrubs only the *source's* credentials from it -- so a sink scrubs
    its own before raising.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class Sink(Protocol):
    """Delivers events to one destination. What a sink target implements.

    Built once when the engine starts and shared by every scan, so `send` must be safe
    to call from several scans' threads at once. Closed when the engine stops.
    """

    def send(self, events: Sequence[Event]) -> None:
        """Deliver every event, or raise `SinkDeliveryError`."""
        ...

    def secrets(self) -> tuple[str, ...]:
        """The destination's secrets, for the caller to scrub from its own logs."""
        ...

    def close(self) -> None: ...


def discovered_agent_event(
    record: DiscoveryOutputRecord,
    config: DiscoverySourceConfigSpec,
    source_name: str,
    observed_at: datetime,
) -> Event:
    """One discovered agent, as the destination receives it.

    `exclude_none` for the reason `GenAIEngineRecordSink` uses it: an optional column is
    absent when a source cannot supply it, so null would turn "this source does not see
    tools" into "this source saw no tools".
    """
    return {
        "event_type": DISCOVERED_AGENT_EVENT,
        "schema_version": EVENT_SCHEMA_VERSION,
        "observed_at": observed_at.isoformat(),
        "source": {
            "id": config.discovery_source_id,
            "name": source_name,
            "vendor": config.vendor,
            "config_name": config.name,
        },
        "agent": record.model_dump(mode="json", exclude_none=True),
    }


def scan_outcome_event(outcome: DiscoveryScanOutcome, source_name: str) -> Event:
    """How one scan ended, so a source that stops working is visible at the destination.

    The payload is the one already written to the log, error included: it was scrubbed
    of the source's credentials when it was recorded, and a delivery failure in it was
    scrubbed of the destination's by the sink that raised it.
    """
    observed_at = outcome.finished_at or datetime.now(timezone.utc)
    return {
        "event_type": SCAN_OUTCOME_EVENT,
        "schema_version": EVENT_SCHEMA_VERSION,
        "observed_at": observed_at.isoformat(),
        "source": {
            "id": outcome.discovery_source_id,
            "name": source_name,
            "vendor": outcome.vendor,
            "config_name": outcome.discovery_source_config_name,
        },
        "outcome": outcome.to_log_payload(),
    }
