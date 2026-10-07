"""The record sink a standalone scan publishes through, whatever the sink target.

`StandaloneRecordSink` takes the place `GenAIEngineRecordSink` has in a Platform job:
`run_source_scan` hands it each batch as it arrives, it turns the batch into events and
hands those to the configured `Sink`, and a batch that cannot be delivered fails the
scan as a publication failure while the batches before it stay delivered.
"""

from datetime import datetime, timezone
from typing import Callable, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discovery_scan import DiscoveryPublishResult
from standalone.sinks.common import Sink, discovered_agent_event


class StandaloneRecordSink:
    """Implements `discovery_scan.DiscoveryRecordSink` for a standalone scan.

    Built per scan with the name of the source being scanned, which the config spec
    does not carry: the spec names the config, and a search at the destination wants
    both.
    """

    def __init__(
        self,
        sink: Sink,
        source_name: str,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._sink = sink
        self._source_name = source_name
        self._clock = clock

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> DiscoveryPublishResult:
        """Send the batch as one event per record.

        `workspace_id` and `data_plane_id` are not sent: a standalone engine has
        neither. Nothing fails per record, because nothing is resolved -- the
        destination takes a record as it is -- so every event lands or this raises. A
        sink may split the batch into several requests, and those before a failing one
        stay delivered; the run counts none of the batch, as it does for any record sink
        that raises, so its count is a lower bound.
        """
        if not records:
            return DiscoveryPublishResult(accepted=0)
        observed_at = self._clock()
        self._sink.send(
            [
                discovered_agent_event(record, config, self._source_name, observed_at)
                for record in records
            ],
        )
        return DiscoveryPublishResult(accepted=len(records))
