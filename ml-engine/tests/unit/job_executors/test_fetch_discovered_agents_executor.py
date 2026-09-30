import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from arthur_client.api_bindings import FetchDiscoveredAgentsJobSpec, RejectedAgent
from genai_client import EnrichedTaskResponse

from job_executors import fetch_discovered_agents_executor
from job_executors.fetch_discovered_agents_executor import (
    MAX_REPORTED_REJECTIONS,
    FetchDiscoveredAgentsExecutor,
    enriched_task_to_agent,
)

WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"
DATA_PLANE_ID = "22222222-2222-2222-2222-222222222222"
SOURCE_ID = "44444444-4444-4444-4444-444444444444"
REPORTED_SINCE = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)


LAST_SEEN = datetime(2026, 9, 16, 22, 0, tzinfo=timezone.utc)
LAST_SCANNED = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)


def _entry(
    resource_id: str,
    source_id: str = SOURCE_ID,
    external_id: str | None = None,
) -> dict[str, object]:
    """A provenance entry as GenAI Engine serves it: one source's report of one record."""
    return {
        "source_class": "siem",
        "source_id": source_id,
        "vendor": "splunk_enterprise",
        "address": {"instance": "splunk.example.com", "resource_id": resource_id},
        "last_seen": LAST_SEEN.isoformat(),
        "last_scanned": LAST_SCANNED.isoformat(),
        "external_id": external_id,
    }


def _task(
    task_id: str,
    sources: list[dict[str, object]] | None = None,
) -> EnrichedTaskResponse:
    return EnrichedTaskResponse.from_dict(
        {
            "id": task_id,
            "name": f"agent-{task_id}",
            "created_at": "2026-09-17T09:00:00Z",
            "updated_at": "2026-09-17T09:00:00Z",
            "is_autocreated": True,
            "num_spans": 0,
            "creation_source": {
                "type": "SIEM",
                "vendor": "splunk_enterprise",
                "address": {"instance": "splunk.example.com", "resource_id": task_id},
                "observations": {"service_names": [f"svc-{task_id}"]},
            },
            "provenance": {
                "sources": (
                    sources
                    if sources is not None
                    else [_entry(task_id, external_id=f"splunk-{task_id}")]
                ),
                "runs_on": "unknown",
                "source_classes": ["siem"],
            },
        },
    )


def _spec(
    reported_since: datetime | None = REPORTED_SINCE,
) -> FetchDiscoveredAgentsJobSpec:
    return FetchDiscoveredAgentsJobSpec(
        workspace_id=WORKSPACE_ID,
        data_plane_id=DATA_PLANE_ID,
        discovery_source_id=SOURCE_ID,
        reported_since=reported_since,
    )


@pytest.fixture
def tasks_api(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """GenAI Engine's agent-tasks endpoint, answering with whatever pages a test sets."""
    api = MagicMock()
    monkeypatch.setattr(
        fetch_discovered_agents_executor,
        "TasksApi",
        lambda _client: api,
    )
    return api


def _agents_client() -> MagicMock:
    """The Agents API, answering each PUT with every agent it was sent."""
    client = MagicMock()
    client.put_agents.side_effect = lambda workspace_id, put_agents: SimpleNamespace(
        agents=put_agents.agents,
        rejected=[],
    )
    return client


def _rejecting_agents_client(rejected_task_ids: set[str]) -> MagicMock:
    """The Agents API storing every agent but these, which it lists in `rejected`."""

    def put(workspace_id: str, put_agents: object) -> SimpleNamespace:
        agents = put_agents.agents  # type: ignore[attr-defined]
        return SimpleNamespace(
            agents=[a for a in agents if a.task_id not in rejected_task_ids],
            rejected=[
                RejectedAgent(
                    index=i,
                    task_id=a.task_id,
                    name=a.name,
                    reason=f"Data plane {DATA_PLANE_ID} does not exist in workspace.",
                )
                for i, a in enumerate(agents)
                if a.task_id in rejected_task_ids
            ],
        )

    client = MagicMock()
    client.put_agents.side_effect = put
    return client


def _job_errors(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Log lines the job exporter would also post as the job's errors."""
    return [
        record.getMessage()
        for record in caplog.records
        if getattr(record, "report_as_job_error", False)
    ]


def _executor(
    agents_client: MagicMock,
    page_size: int = 2,
) -> FetchDiscoveredAgentsExecutor:
    return FetchDiscoveredAgentsExecutor(
        agents_client=agents_client,
        logger=logging.getLogger("test-fetch-discovered-agents"),
        genai_engine_url="http://genai",
        genai_engine_api_key="key",
        page_size=page_size,
    )


def _uploaded_task_ids(agents_client: MagicMock) -> list[list[str]]:
    return [
        [agent.task_id for agent in c.kwargs["put_agents"].agents]
        for c in agents_client.put_agents.call_args_list
    ]


def test_fetches_the_one_source_in_its_window_and_uploads_every_page(
    tasks_api: MagicMock,
) -> None:
    """Pages are requested until a short one says it was the last, and each is
    uploaded as it arrives rather than after the last."""
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [
        [_task("t1"), _task("t2")],
        [_task("t3"), _task("t4")],
        [_task("t5")],
    ]
    agents_client = _agents_client()

    _executor(agents_client).execute(_spec())

    requests = tasks_api.get_agent_tasks_api_v2_agent_tasks_get.call_args_list
    assert [c.kwargs["after_task_id"] for c in requests] == [None, "t2", "t4"]
    for c in requests:
        assert c.kwargs["discovery_source_id"] == SOURCE_ID
        assert c.kwargs["reported_since"] == REPORTED_SINCE
        assert c.kwargs["page_size"] == 2
    assert _uploaded_task_ids(agents_client) == [["t1", "t2"], ["t3", "t4"], ["t5"]]
    for c in agents_client.put_agents.call_args_list:
        assert c.kwargs["workspace_id"] == WORKSPACE_ID


def test_a_full_last_page_is_followed_by_an_empty_one_and_nothing_more(
    tasks_api: MagicMock,
) -> None:
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [
        [_task("t1"), _task("t2")],
        [],
    ]
    agents_client = _agents_client()

    _executor(agents_client).execute(_spec())

    assert tasks_api.get_agent_tasks_api_v2_agent_tasks_get.call_count == 2
    # an empty page is not uploaded: PUT would be a no-op request
    assert _uploaded_task_ids(agents_client) == [["t1", "t2"]]


def test_the_standalone_fetch_reads_everything_the_source_ever_reported(
    tasks_api: MagicMock,
) -> None:
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [[]]

    _executor(_agents_client()).execute(_spec(reported_since=None))

    [request] = tasks_api.get_agent_tasks_api_v2_agent_tasks_get.call_args_list
    assert request.kwargs["reported_since"] is None


def test_fetching_twice_uploads_the_same_agents_under_the_same_task_ids(
    tasks_api: MagicMock,
) -> None:
    """Idempotency is the Platform's upsert on task_id; what this job owes it is
    handing over the same task_id for the same task on every run."""
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [
        [_task("t1")],
        [_task("t1")],
    ]
    agents_client = _agents_client()
    executor = _executor(agents_client)

    executor.execute(_spec())
    executor.execute(_spec())

    assert _uploaded_task_ids(agents_client) == [["t1"], ["t1"]]


def test_an_upload_failure_fails_the_job_after_the_pages_before_it_landed(
    tasks_api: MagicMock,
) -> None:
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [
        [_task("t1"), _task("t2")],
        [_task("t3")],
    ]
    agents_client = MagicMock()
    agents_client.put_agents.side_effect = [
        SimpleNamespace(agents=[MagicMock(), MagicMock()], rejected=[]),
        RuntimeError("platform down"),
    ]

    with pytest.raises(RuntimeError, match="platform down"):
        _executor(agents_client).execute(_spec())

    assert agents_client.put_agents.call_count == 2


def test_an_agent_carries_its_task_and_its_provenance() -> None:
    agent = enriched_task_to_agent(_task("t1"), DATA_PLANE_ID)

    assert agent.task_id == "t1"
    assert agent.data_plane_id == DATA_PLANE_ID
    assert agent.provenance is not None
    [source] = agent.provenance.sources
    assert source.source_id == SOURCE_ID
    assert source.vendor == "splunk_enterprise"


def test_the_fetch_job_uploads_provenance(tasks_api: MagicMock) -> None:
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [[_task("t1")]]
    agents_client = _agents_client()

    _executor(agents_client).execute(_spec())

    [agent] = agents_client.put_agents.call_args.kwargs["put_agents"].agents
    assert agent.provenance is not None
    # And its own source's evidence, which is what the Platform keys records on.
    [record] = agent.evidence
    assert record.external_id == "splunk-t1"
    assert str(record.source_id) == SOURCE_ID


# --- evidence (UP-4993) -----------------------------------------------------------


def test_each_record_the_source_reported_becomes_its_evidence() -> None:
    """One source finds one agent twice -- two records, two pieces of evidence -- and
    each is dated by the source's sighting and the last scan that reported it."""
    task = _task(
        "t1",
        sources=[
            _entry("t1", external_id="splunk-t1"),
            _entry("rec-2", external_id="splunk-rec-2"),
        ],
    )

    agent = enriched_task_to_agent(task, DATA_PLANE_ID, SOURCE_ID)

    by_record = {record.external_id: record for record in agent.evidence}
    assert set(by_record) == {"splunk-t1", "splunk-rec-2"}
    record = by_record["splunk-rec-2"]
    assert str(record.source_id) == SOURCE_ID
    assert record.last_seen == LAST_SEEN
    assert record.last_scanned == LAST_SCANNED
    # Derived by the Platform from the sightings it receives, so never sent.
    assert record.first_seen is None
    source = record.creation_source.actual_instance
    assert source.type == "SIEM"
    assert source.vendor == "splunk_enterprise"
    assert source.address.resource_id == "rec-2"


def test_only_the_record_the_task_came_from_carries_its_observations() -> None:
    """Observations travel on the task's creation source, which is one record's."""
    task = _task(
        "t1",
        sources=[
            _entry("t1", external_id="splunk-t1"),
            _entry("rec-2", external_id="splunk-rec-2"),
        ],
    )

    agent = enriched_task_to_agent(task, DATA_PLANE_ID, SOURCE_ID)

    observed = {
        record.external_id: record.creation_source.actual_instance.observations
        for record in agent.evidence
    }
    assert observed["splunk-t1"].service_names == ["svc-t1"]
    assert observed["splunk-rec-2"] is None


def test_the_creation_record_keeps_its_observations_when_its_address_moves() -> None:
    """An entry holds the latest scan's address. A Jamf record's address is its
    device's primary route to the agent, which changes when that route is uninstalled
    though the record does not; the one record left on the same instance is it."""
    task = _task("t1", sources=[_entry("another-route", external_id="splunk-t1")])

    agent = enriched_task_to_agent(task, DATA_PLANE_ID, SOURCE_ID)

    [record] = agent.evidence
    assert record.creation_source.actual_instance.observations.service_names == [
        "svc-t1"
    ]


def test_observations_go_nowhere_when_the_creation_record_cannot_be_told() -> None:
    """Two records on the instance, neither at the creation source's address: pinning
    the observations on either could put them on the wrong one."""
    task = _task(
        "t1",
        sources=[
            _entry("route-2", external_id="splunk-2"),
            _entry("route-3", external_id="splunk-3"),
        ],
    )

    agent = enriched_task_to_agent(task, DATA_PLANE_ID, SOURCE_ID)

    assert len(agent.evidence) == 2
    assert all(
        record.creation_source.actual_instance.observations is None
        for record in agent.evidence
    )


def test_other_sources_entries_are_left_to_their_own_fetch() -> None:
    other_source = "55555555-5555-5555-5555-555555555555"
    task = _task(
        "t1",
        sources=[
            _entry("t1", external_id="splunk-t1"),
            _entry("rec-9", source_id=other_source, external_id="other-rec-9"),
        ],
    )

    agent = enriched_task_to_agent(task, DATA_PLANE_ID, SOURCE_ID)

    assert [record.external_id for record in agent.evidence] == ["splunk-t1"]
    # Provenance still names both sources: it is the task's, not the fetch's.
    assert len(agent.provenance.sources) == 2


def test_an_entry_that_does_not_name_its_record_uploads_no_evidence() -> None:
    """A GenAI Engine that predates serving `external_id`: the record cannot be keyed,
    so the agent goes up without evidence and the Platform lifts its creation source,
    as it did before."""
    task = _task("t1", sources=[_entry("t1")])

    agent = enriched_task_to_agent(task, DATA_PLANE_ID, SOURCE_ID)

    assert not agent.evidence


def test_an_upload_with_no_discovery_source_carries_no_evidence() -> None:
    """The legacy GCP sweep publishes tasks it did not fetch for any source."""
    agent = enriched_task_to_agent(_task("t1"), DATA_PLANE_ID)

    assert not agent.evidence


# --- agents the Platform does not store (UP-5069) ---------------------------------


def test_an_agent_the_platform_rejects_is_a_job_error_and_the_rest_still_count(
    tasks_api: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The Platform stores the rest of the batch and lists the refused ones, so the
    PUT succeeds either way; the refused agent has to surface somewhere a person
    looks, or its task simply never appears."""
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [
        [_task("a"), _task("b"), _task("c")],
    ]
    agents_client = _rejecting_agents_client({"b"})

    with caplog.at_level(logging.INFO):
        _executor(agents_client, page_size=5).execute(_spec())

    assert _job_errors(caplog) == [
        f"Agents API did not store the agent for task b (agent-b): Data plane "
        f"{DATA_PLANE_ID} does not exist in workspace.",
    ]
    assert "Uploaded 2 agent(s)" in caplog.text, "only what landed is counted"


def test_a_batch_refused_wholesale_is_summarized_rather_than_listed_in_full(
    tasks_api: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each reported rejection is a log line and a job error, so a thousand refused
    agents must not become two thousand calls to the Platform."""
    task_ids = [f"t{i}" for i in range(MAX_REPORTED_REJECTIONS + 5)]
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [
        [_task(task_id) for task_id in task_ids],
    ]

    with caplog.at_level(logging.ERROR):
        _executor(
            _rejecting_agents_client(set(task_ids)),
            page_size=len(task_ids) + 1,
        ).execute(_spec())

    errors = _job_errors(caplog)
    assert len(errors) == MAX_REPORTED_REJECTIONS + 1
    assert errors[-1] == (
        f"Agents API did not store {len(task_ids)} agent(s) in all; the first "
        f"{MAX_REPORTED_REJECTIONS} are listed above."
    )


def test_a_platform_that_predates_rejected_reports_nothing_extra(
    tasks_api: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An older Platform omits `rejected`, which the client reads back as None."""
    tasks_api.get_agent_tasks_api_v2_agent_tasks_get.side_effect = [[_task("a")]]
    agents_client = MagicMock()
    agents_client.put_agents.side_effect = lambda workspace_id, put_agents: (
        SimpleNamespace(agents=put_agents.agents, rejected=None)
    )

    with caplog.at_level(logging.ERROR):
        _executor(agents_client, page_size=5).execute(_spec())

    assert _job_errors(caplog) == []
