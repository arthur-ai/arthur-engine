import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from arthur_client.api_bindings import FetchDiscoveredAgentsJobSpec
from genai_client import EnrichedTaskResponse

from job_executors import fetch_discovered_agents_executor
from job_executors.fetch_discovered_agents_executor import (
    FetchDiscoveredAgentsExecutor,
    enriched_task_to_agent,
)

WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"
DATA_PLANE_ID = "22222222-2222-2222-2222-222222222222"
SOURCE_ID = "44444444-4444-4444-4444-444444444444"
REPORTED_SINCE = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)


def _task(task_id: str) -> EnrichedTaskResponse:
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
            },
            "provenance": {
                "sources": [
                    {
                        "source_class": "siem",
                        "source_id": SOURCE_ID,
                        "vendor": "splunk_enterprise",
                    },
                ],
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
    )
    return client


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
        SimpleNamespace(agents=[MagicMock(), MagicMock()]),
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
