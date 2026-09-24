"""Publishing a scan's records: the handoff from a connector to GenAI Engine.

`run_source_scan` hands each batch here as it arrives, and this resolves it onto tasks
through `POST /api/v2/agent-tasks/resolve` (D-08). That endpoint owns identity -- the
resolution ladder, and the guarantee that re-submitting a record lands it on the same
task -- so nothing in this module decides what a record means. What it owns is the trip:
batching to the endpoint's limit, converting between two models of the same shape, and
reporting what came back.

BESIDE THE SEAM RATHER THAN IN `discovery/`, for the reason the output contract is: that
package is the connectors, and importing it registers them.
"""

import logging
from typing import Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import (
    MAX_DISCOVERED_RECORDS_PER_REQUEST,
    DiscoveryOutputRecord,
)
from genai_client import (
    ApiClient,
    Configuration,
)
from genai_client import DiscoveredAgentRecord as WireRecord
from genai_client import (
    ResolveDiscoveredAgentsRequest,
    TasksApi,
)

from job_executors.discovery_scan import DiscoveryPublishResult, FailedDiscoveryRecord


class GenAIEngineRecordSink:
    """Implements `discovery_scan.DiscoveryRecordSink`."""

    def __init__(
        self,
        genai_engine_url: str,
        genai_engine_api_key: str,
        logger: logging.Logger,
        chunk_size: int = MAX_DISCOVERED_RECORDS_PER_REQUEST,
    ) -> None:
        self._url = genai_engine_url
        self._key = genai_engine_api_key
        self._log = logger
        # Never above the endpoint's own cap, whatever a caller asks for: the limit is
        # declared in arthur_common so both ends read one number, and a request over it
        # is refused whole rather than truncated.
        self._chunk = max(1, min(chunk_size, MAX_DISCOVERED_RECORDS_PER_REQUEST))
        self._client: Optional[ApiClient] = None

    def _tasks(self) -> TasksApi:
        """One client for the sink's life.

        A fleet scan publishes once per device, so building a client per batch would
        open and discard ten thousand connection pools in a run. Each job gets its own
        executor and therefore its own sink, so nothing is shared between concurrent
        scans running as threads in one interpreter.

        There is nothing to close afterwards: the generated client's `__exit__` is a
        no-op and it exposes no `close`, so a teardown method here would promise a
        cleanup that does not happen.
        """
        if self._client is None:
            self._client = ApiClient(
                Configuration(host=self._url, access_token=self._key),
            )
        return TasksApi(self._client)

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> DiscoveryPublishResult:
        """Resolve one batch, in chunks the endpoint will accept.

        `workspace_id` and `data_plane_id` are not sent: the resolve endpoint scopes by
        the credential the request carries, so passing them would be inventing a second
        answer to a question already settled at authentication.
        """
        if not records:
            # The request declares `min_length=1`, so an empty batch is a 422 rather
            # than a no-op. The caller already skips these; this is the guard for the
            # connector that yields one anyway.
            return DiscoveryPublishResult(accepted=0)

        accepted = 0
        failed: list[FailedDiscoveryRecord] = []

        for start in range(0, len(records), self._chunk):
            chunk = records[start : start + self._chunk]
            response = (
                self._tasks().resolve_discovered_agents_api_v2_agent_tasks_resolve_post(
                    ResolveDiscoveredAgentsRequest(
                        records=[_as_wire(r) for r in chunk],
                    ),
                )
            )
            accepted += len(response.resolved)
            failed.extend(
                FailedDiscoveryRecord(
                    external_id=f.external_id,
                    reason=str(getattr(f.reason, "value", f.reason)),
                    detail=f.detail,
                )
                for f in (response.failed or [])
            )

        if failed:
            # Reported once per batch rather than per record: a source misconfigured
            # against a deleted task fails every record it produces, and one line each
            # would bury the run's own outcome.
            self._log.warning(
                "Source config '%s': %s of %s record(s) could not be resolved (%s)",
                config.name,
                len(failed),
                len(records),
                ", ".join(sorted({f.reason for f in failed})),
            )

        return DiscoveryPublishResult(accepted=accepted, failed=tuple(failed))


def _as_wire(record: DiscoveryOutputRecord) -> WireRecord:
    """One record in the shape the generated client posts.

    Two generated models of the same contract -- arthur_common's and genai_client's --
    so this crosses between them through the JSON they both agree on rather than by
    field assignment, which would need editing whenever either gains a column.

    BUILT THROUGH `from_dict`, NEVER BY HANDING THE DICT TO THE CONSTRUCTOR.
    `creation_source` generates as a oneOf wrapper, and the constructor accepts a plain
    dict for it without resolving which member it is: the wrapper's `actual_instance`
    stays None, `to_dict()` then returns None for the field, and every record publishes
    with no vendor, no address and no observations. It validates, it serializes, and the
    sensor attribution is gone. `from_dict` resolves the member, so a record whose
    creation source does not match one fails loudly here instead.

    `exclude_none` is the contract, not a size saving. An optional column is absent when
    a source cannot supply it and null never means anything else, so sending null would
    turn "this sensor does not see tools" into "this sensor saw no tools".
    """
    wire = WireRecord.from_dict(record.model_dump(mode="json", exclude_none=True))
    if wire is None:  # pragma: no cover -- from_dict only returns None for a None input
        raise ValueError(
            f"record {record.external_id!r} did not convert to the wire model",
        )
    return wire
