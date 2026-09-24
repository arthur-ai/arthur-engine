import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import (
    MAX_DISCOVERED_RECORDS_PER_REQUEST,
    DiscoveredAgentRecord,
)
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    EndpointAgentCreationSource,
    SourceAddress,
)
from genai_client import ApiClient, Configuration
from genai_client import DiscoveredRecordFailureReason as WireReason
from genai_client import FailedDiscoveredRecord as WireFailed
from genai_client import ResolvedAgentTask as WireResolved
from genai_client import ResolveDiscoveredAgentsResponse as WireResponse
from genai_client import TaskResolutionMethod as WireMethod

from job_executors import discovery_record_sink as sink_module
from job_executors.discovery_record_sink import GenAIEngineRecordSink

SOURCE_ID = "44444444-4444-4444-4444-444444444444"


def _config() -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id=SOURCE_ID,
        name="jamf prod",
        vendor="jamf_pro",
        query="",
        query_language="none",
        lookback_window_seconds=3600,
    )


def _record(external_id: str = "m1:codex-cli") -> DiscoveredAgentRecord:
    """A record shaped the way the Jamf connector emits one."""
    return DiscoveredAgentRecord(
        external_id=external_id,
        name="Codex CLI",
        last_seen=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
        creation_source=EndpointAgentCreationSource(
            vendor="jamf_pro",
            address=SourceAddress(
                instance="m1",
                resource_kind="npm",
                resource_id="@openai/codex",
            ),
            observations=AgentObservations(version="0.5.0", host_name="mac-m1"),
        ),
    )


class FakeTasks:
    """Stands in for the generated TasksApi, keeping every request it is handed."""

    def __init__(self, responses: Optional[list[WireResponse]] = None) -> None:
        self.requests: list[Any] = []
        self.timeouts: list[Any] = []
        self._responses = list(responses or [])

    def resolve_discovered_agents_api_v2_agent_tasks_resolve_post(
        self,
        request: Any,
        _request_timeout: Any = None,
    ) -> WireResponse:
        self.requests.append(request)
        self.timeouts.append(_request_timeout)
        if self._responses:
            return self._responses.pop(0)
        return WireResponse(
            resolved=[
                WireResolved(
                    external_id=r.external_id,
                    task_id=f"task-{r.external_id}",
                    name=r.name,
                    resolved_by=WireMethod.EXTERNAL_ID,
                )
                for r in request.records
            ],
            failed=[],
        )


@pytest.fixture
def tasks(monkeypatch: pytest.MonkeyPatch) -> FakeTasks:
    fake = FakeTasks()
    monkeypatch.setattr(sink_module, "ApiClient", lambda *a, **k: object())
    monkeypatch.setattr(sink_module, "TasksApi", lambda client: fake)
    return fake


def _sink(
    chunk_size: int = MAX_DISCOVERED_RECORDS_PER_REQUEST,
) -> GenAIEngineRecordSink:
    return GenAIEngineRecordSink(
        genai_engine_url="http://genai.invalid",
        genai_engine_api_key="key",
        logger=logging.getLogger("test-sink"),
        chunk_size=chunk_size,
    )


def _body(request: Any) -> dict[str, Any]:
    """The request as it actually goes on the wire, through the client's serializer."""
    serialized = ApiClient(
        Configuration(host="http://genai.invalid"),
    ).sanitize_for_serialization(request)
    return json.loads(json.dumps(serialized))


# --- the sensor attribution, which is the whole point of the trip ------------------


def test_the_creation_source_reaches_the_wire(tasks: FakeTasks) -> None:
    """`creation_source` generates as a oneOf wrapper, and handing its dict to the
    constructor leaves `actual_instance` unset: the field validates, serializes as null,
    and every record publishes with no vendor, no address and no observations. Asserted
    on the serialized body rather than the model, because the model looked right."""
    _sink().publish("ws", "dp", _config(), [_record()])

    body = _body(tasks.requests[0])
    source = body["records"][0]["creation_source"]
    assert source is not None, "the sensor that found the agent was dropped"
    assert source["vendor"] == "jamf_pro"
    assert source["address"]["instance"] == "m1"
    assert source["address"]["resource_id"] == "@openai/codex"
    assert source["observations"]["version"] == "0.5.0"


def test_an_unsupplied_column_is_never_an_empty_list(tasks: FakeTasks) -> None:
    """Absent and null both deserialize to None, so the generated client is free to
    send either -- and it sends null, because its `from_dict` sets every column
    explicitly. What must never happen is an empty list: that says the sensor looked
    and found none, which is a different claim from not being able to look."""
    _sink().publish("ws", "dp", _config(), [_record()])

    record = _body(tasks.requests[0])["records"][0]
    for column in ("tools", "llm_models", "sub_agents", "data_sources"):
        assert record.get(column) is None, f"{column} was fabricated as a reading"


def test_the_record_keeps_its_own_last_seen(tasks: FakeTasks) -> None:
    """The payload dates itself; the poll time would date every finding to now."""
    _sink().publish("ws", "dp", _config(), [_record()])
    body = _body(tasks.requests[0])
    assert body["records"][0]["last_seen"].startswith("2026-09-17T12:00:00")


# --- batching ---------------------------------------------------------------------


def test_a_batch_over_the_endpoint_limit_is_split(tasks: FakeTasks) -> None:
    records = [_record(f"m{i}:codex-cli") for i in range(5)]
    result = _sink(chunk_size=2).publish("ws", "dp", _config(), records)

    assert [len(r.records) for r in tasks.requests] == [2, 2, 1]
    assert result.accepted == 5, "every chunk's resolutions count toward the run"


def test_a_caller_cannot_raise_the_chunk_above_the_endpoint_cap(
    tasks: FakeTasks,
) -> None:
    """The limit is declared in arthur_common so both ends read one number, and a
    request over it is refused whole rather than truncated."""
    sink = _sink(chunk_size=MAX_DISCOVERED_RECORDS_PER_REQUEST + 500)
    assert sink._chunk == MAX_DISCOVERED_RECORDS_PER_REQUEST


def test_an_empty_batch_is_never_sent(tasks: FakeTasks) -> None:
    """The request declares min_length=1, so an empty batch is a 422 rather than a
    no-op."""
    result = _sink().publish("ws", "dp", _config(), [])
    assert tasks.requests == []
    assert result.accepted == 0


def test_one_client_serves_every_batch(tasks: FakeTasks) -> None:
    """A fleet scan publishes once per device, so a client per batch would open and
    discard ten thousand connection pools in a run."""
    sink = _sink()
    for i in range(3):
        sink.publish("ws", "dp", _config(), [_record(f"m{i}:codex-cli")])
    assert len(tasks.requests) == 3
    assert sink._client is not None


def test_every_request_carries_a_finite_timeout(tasks: FakeTasks) -> None:
    """The generated client defaults to `_request_timeout=None`, which is urllib3's
    wait-forever. A scan job is a thread in the runner, so an engine that accepts the
    connection and then stalls blocks it for the life of the process -- and the run
    never fails, because finalize_outcome sits in a `finally` never reached."""
    records = [_record(f"m{i}:codex-cli") for i in range(3)]
    _sink(chunk_size=1).publish("ws", "dp", _config(), records)

    assert len(tasks.timeouts) == 3, "every chunk, not just the first"
    for timeout in tasks.timeouts:
        connect, read = timeout
        assert connect > 0 and read > 0


# --- what came back ---------------------------------------------------------------


def test_a_failed_record_does_not_fail_its_batch(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GenAI Engine resolves the rest and reports the failure alongside them. A failure
    is final for that input, so it is reported on the run and never retried."""
    response = WireResponse(
        resolved=[
            WireResolved(
                external_id="m1:codex-cli",
                task_id="task-1",
                name="Codex CLI",
                resolved_by=WireMethod.CREATED,
            ),
        ],
        failed=[
            WireFailed(
                external_id="m2:codex-cli",
                task_id="ghost",
                reason=WireReason.TASK_NOT_FOUND,
                detail="task ghost does not exist",
            ),
        ],
    )
    fake = FakeTasks([response])
    monkeypatch.setattr(sink_module, "ApiClient", lambda *a, **k: object())
    monkeypatch.setattr(sink_module, "TasksApi", lambda client: fake)

    with caplog.at_level(logging.WARNING):
        result = _sink().publish(
            "ws",
            "dp",
            _config(),
            [_record("m1:codex-cli"), _record("m2:codex-cli")],
        )

    assert result.accepted == 1, "the resolved record still counts"
    assert [f.external_id for f in result.failed] == ["m2:codex-cli"]
    assert result.failed[0].reason == "task_not_found"
    assert result.failed[0].detail == "task ghost does not exist"
    assert "jamf prod" in caplog.text and "task_not_found" in caplog.text


def test_the_reason_crosses_as_a_string_not_a_generated_enum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The run outcome D-11 persists must not change shape when the client is
    regenerated, which is why FailedDiscoveryRecord is declared engine-side."""
    fake = FakeTasks(
        [
            WireResponse(
                resolved=[],
                failed=[
                    WireFailed(
                        external_id="m1:codex-cli",
                        task_id="ghost",
                        reason=WireReason.TASK_NOT_FOUND,
                        detail="gone",
                    ),
                ],
            ),
        ],
    )
    monkeypatch.setattr(sink_module, "ApiClient", lambda *a, **k: object())
    monkeypatch.setattr(sink_module, "TasksApi", lambda client: fake)

    result = _sink().publish("ws", "dp", _config(), [_record()])
    assert isinstance(result.failed[0].reason, str)
    assert not isinstance(result.failed[0].reason, WireReason)
