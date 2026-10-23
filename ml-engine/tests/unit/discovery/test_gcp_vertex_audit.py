"""The Vertex AI Data Access audit log read by the gcp_vertex source.

The fixture is real audit entries from a demo project, with the project, project
number and the one person's address replaced: three GenerateContent calls by a
workload's service account, one by the Agent Engine service agent, and one Agent Engine
query by a person.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import pytest
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import CloudAgentCreationSource
from google.auth.credentials import Credentials
from google.auth.exceptions import GoogleAuthError

from discovery.cloud.gcp_vertex.audit import (
    DEFAULT_LOOKBACK,
    MODEL_CALL_METHODS,
    AuditCounts,
    AuditReadError,
    audit_filter,
    audit_records,
    fold,
    read_entries,
    since_for,
)
from discovery.cloud.gcp_vertex.connector import (
    READ_AUDIT_LOGS_FIELD,
    VertexAgentEngineConnector,
    settings_from,
)

ENTRIES = json.loads(
    (Path(__file__).parent / "fixtures" / "vertex_data_access_entries.json").read_text()
)
WORKLOAD = "123456789012-compute@developer.gserviceaccount.com"
NOW = datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc)
LOG = logging.getLogger("test.vertex_audit")


class Reader:
    def __init__(
        self, entries: Iterable[dict[str, Any]] = ENTRIES, error: Any = None
    ) -> None:
        self.entries = list(entries)
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def __call__(
        self, project: str, log_filter: str, credentials: Optional[Credentials]
    ) -> Iterable[dict[str, Any]]:
        self.calls.append((project, log_filter))
        if self.error is not None:
            raise self.error
        return iter(self.entries)


def records(reader: Reader, lookback_hours: int = 24) -> list[Any]:
    return audit_records(
        reader, "demo-project", None, lookback_hours, NOW, "gcp_vertex", LOG
    )


def test_a_workload_calling_gemini_is_one_record_per_account_and_region() -> None:
    (record,) = records(Reader())
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == "gcp_vertex"
    assert (
        source.address.instance,
        source.address.scope,
        source.address.resource_kind,
        source.address.resource_id,
    ) == ("demo-project", "us-central1", "service_account", WORKLOAD)
    assert record.external_id == (
        f"projects/demo-project/locations/us-central1/serviceAccounts/{WORKLOAD}"
    )
    assert [m.name for m in record.llm_models or []] == ["gemini-2.5-flash"]
    assert record.name == "123456789012-compute calling gemini-2.5-flash"
    assert record.last_seen == max(
        datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")[:26] + "+00:00")
        for e in ENTRIES
        if e["protoPayload"]["authenticationInfo"]["principalEmail"] == WORKLOAD
    )


def test_the_agent_engine_service_agent_and_people_are_counted_not_reported() -> None:
    """The listing already reports Agent Engine agents; a person is not a workload and
    their address is personal data."""
    counts = AuditCounts()
    callers = fold(ENTRIES, counts)
    assert set(callers) == {(WORKLOAD, "us-central1")}
    assert counts.calls == 3
    assert counts.agent_engine_calls == 1
    # the person's entry is an Agent Engine query, not a model path: unreadable here
    assert counts.user_calls + counts.unparsed == 1


def test_a_person_calling_a_model_is_never_named() -> None:
    entry = json.loads(json.dumps(ENTRIES[0]))
    entry["protoPayload"]["authenticationInfo"]["principalEmail"] = "a@example.com"
    counts = AuditCounts()
    assert fold([entry], counts) == {}
    assert counts.user_calls == 1


def test_the_filter_names_model_calls_in_the_project_since_the_lookback() -> None:
    reader = Reader()
    records(reader, lookback_hours=6)
    ((project, log_filter),) = reader.calls
    assert project == "demo-project"
    assert (
        'logName="projects/demo-project/logs/cloudaudit.googleapis.com%2Fdata_access"'
        in log_filter
    )
    assert 'protoPayload.serviceName="aiplatform.googleapis.com"' in log_filter
    for method in MODEL_CALL_METHODS:
        assert f'"PredictionService.{method}"' in log_filter
    assert "ListReasoningEngines" not in log_filter
    assert 'timestamp>="2026-10-20T18:00:00+00:00"' in log_filter


def test_a_lookback_of_zero_reads_thirty_days() -> None:
    assert since_for(0, NOW) == NOW - DEFAULT_LOOKBACK
    assert 'timestamp>="2026-09-21' in audit_filter("p", since_for(0, NOW))


def test_a_refused_read_is_a_warning_not_a_failed_scan(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        assert records(Reader(error=AuditReadError(403, "denied"))) == []
    assert "roles/logging.privateLogViewer" in caplog.text


def test_an_empty_window_says_the_log_may_be_off(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        assert records(Reader(entries=[])) == []
    assert "Data Access audit logs are enabled" in caplog.text


def test_the_toggle_is_off_unless_set() -> None:
    assert settings_from({"project_id": "p"}).read_audit_logs is False
    assert settings_from(
        {"project_id": "p", READ_AUDIT_LOGS_FIELD: "true"}
    ).read_audit_logs


def scan(fields: dict[str, str], reader: Reader) -> list[Any]:
    connector = VertexAgentEngineConnector(
        lister=lambda settings, credentials: [],
        audit_reader=reader,
        clock=lambda: NOW,
    )
    config = DiscoverySourceConfigSpec.model_construct(
        name="vertex", vendor="gcp_vertex", query=None
    )
    out: list[Any] = []
    for batch in connector.scan(config, 24, {}, fields, LOG):
        out.extend(batch)
    return out


def test_the_connector_reads_the_audit_log_only_when_asked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARTHUR_ENGINE_GCP_VERTEX_ALLOW_ADC", "true")
    monkeypatch.setattr("google.auth.default", lambda scopes=None: (None, None))
    off = Reader()
    assert scan({"project_id": "demo-project"}, off) == []
    assert off.calls == []
    on = Reader()
    found = scan({"project_id": "demo-project", READ_AUDIT_LOGS_FIELD: "true"}, on)
    assert [r.creation_source.address.resource_id for r in found] == [WORKLOAD]


def test_claude_on_vertex_is_a_model_call_named_by_its_publisher_model() -> None:
    """Partner models (Anthropic's Claude on Vertex) are called with rawPredict and
    streamRawPredict. The entry below is shaped from Vertex's documented request path
    for partner models, not captured from a live call."""
    entry = {
        "timestamp": "2026-10-20T23:40:00.123456789Z",
        "protoPayload": {
            "serviceName": "aiplatform.googleapis.com",
            "methodName": "google.cloud.aiplatform.v1.PredictionService.RawPredict",
            "resourceName": (
                "projects/demo-project/locations/us-east5/publishers/anthropic/"
                "models/claude-sonnet-4-5"
            ),
            "authenticationInfo": {"principalEmail": WORKLOAD},
        },
    }
    assert "RawPredict" in MODEL_CALL_METHODS
    assert "StreamRawPredict" in MODEL_CALL_METHODS
    counts = AuditCounts()
    (caller,) = fold([entry], counts).values()
    assert (caller.location, caller.models) == ("us-east5", {"claude-sonnet-4-5"})


@pytest.mark.parametrize(
    "error",
    [
        requests.ConnectionError("reset"),
        GoogleAuthError("no token"),
        ValueError("not json"),
    ],
)
def test_a_failed_read_of_any_kind_leaves_the_listing_alone(
    error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        assert records(Reader(error=error)) == []
    assert "listing is unaffected" in caplog.text


def test_a_repeated_page_token_stops_the_read(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {"entries": [], "nextPageToken": "same"}

    class Session:
        posts = 0

        def __init__(self, credentials: Any) -> None:
            pass

        def post(self, *args: Any, **kwargs: Any) -> Response:
            Session.posts += 1
            return Response()

    monkeypatch.setattr("discovery.cloud.gcp_vertex.audit.AuthorizedSession", Session)
    with pytest.raises(AuditReadError, match="repeated a page token"):
        list(read_entries("demo-project", "filter", object()))  # type: ignore[arg-type]
    assert Session.posts == 2
