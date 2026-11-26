"""The record sink a standalone scan publishes through, whatever the sink target.

`StandaloneRecordSink` takes the place `GenAIEngineRecordSink` has in a Platform job:
`run_source_scan` hands it each batch as it arrives, it turns the batch into events and
hands those to the configured `Sink`, and a batch that cannot be delivered fails the
scan as a publication failure while the batches before it stay delivered. An event the
destination refuses on its own is a failed record instead.
"""

from datetime import datetime, timezone
from typing import Callable, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discovery_scan import (
    CorroboratingRecord,
    DiscoveryPublishResult,
    FailedDiscoveryRecord,
    McpServerRecord,
)
from standalone.sinks.common import Sink, discovered_agent_event, mcp_server_event


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
        neither. A record fails when the destination refuses its event alone -- a
        field its mapping cannot take -- and is reported on the scan's outcome while
        the rest go on, as a record GenAI Engine cannot resolve is. A sink that raises
        did not complete a request; it may have split the batch into several, and those
        before the failing one stay delivered, but the run counts none of the batch, as
        it does for any record sink that raises, so its count is a lower bound.

        A `CorroboratingRecord` is not sent. It exists to put a further piece of
        evidence on its agent's task, and an event per record would report the agent
        once for each.

        An `McpServerRecord` is sent as an MCP server event and counted apart from
        the agents, so `accepted` stays a count of agents.
        """
        sent = [r for r in records if not isinstance(r, CorroboratingRecord)]
        if not sent:
            return DiscoveryPublishResult(accepted=0)
        observed_at = self._clock()
        refused = self._sink.send(
            [
                (
                    mcp_server_event(record, config, self._source_name, observed_at)
                    if isinstance(record, McpServerRecord)
                    else discovered_agent_event(
                        record,
                        config,
                        self._source_name,
                        observed_at,
                    )
                )
                for record in sent
            ],
        )
        # A refusal's position is into the events sent, which leave corroborating
        # records out, so it names one of `sent`, not of `records`.
        failed = tuple(
            FailedDiscoveryRecord(
                external_id=sent[r.position].external_id,
                reason=r.reason,
                detail=r.detail,
            )
            for r in refused
        )
        refused_at = {r.position for r in refused}
        servers = sum(
            isinstance(record, McpServerRecord) and position not in refused_at
            for position, record in enumerate(sent)
        )
        return DiscoveryPublishResult(
            accepted=len(sent) - len(refused_at) - servers,
            failed=failed,
            mcp_servers=servers,
        )
