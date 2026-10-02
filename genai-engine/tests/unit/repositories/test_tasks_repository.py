import uuid
from datetime import datetime, timedelta

import pytest
from arthur_common.models.agent_governance_schemas import (
    AgentCreationSource,
    CloudAgentCreationSource,
    EndpointAgentCreationSource,
    GCPAgentCreationSource,
    ManualAgentCreationSource,
    OTELAgentCreationSource,
    SIEMAgentCreationSource,
    SourceAddress,
    TaskMetadata,
)
from arthur_common.models.enums import PaginationSortMethod

from db_models import DatabaseTask
from db_models.telemetry_models import DatabaseTraceMetadata
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.enums import TaskSortField
from schemas.internal_schemas import Task
from tests.clients.base_test_client import override_get_db_session
from utils.constants import DEFAULT_ORG_ID


def _build_repo(db_session):
    application_config = get_application_config(session=db_session)
    rules_repo = RuleRepository(db_session)
    metric_repo = MetricRepository(db_session)
    return TaskRepository(db_session, rules_repo, metric_repo, application_config)


def _add_task(client, db_session, name, created_at, updated_at=None):
    sc, task = client.create_task(name=name)
    assert sc == 200
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task.id).update(
        {"created_at": created_at, "updated_at": updated_at or created_at},
    )
    db_session.commit()
    return task.id


def _add_trace(db_session, task_id, end_time, org_id=DEFAULT_ORG_ID):
    trace = DatabaseTraceMetadata(
        trace_id=str(uuid.uuid4()),
        task_id=task_id,
        org_id=org_id,
        session_id=None,
        user_id=None,
        span_count=1,
        start_time=end_time,
        end_time=end_time,
        created_at=end_time,
        updated_at=end_time,
        input_content="in",
        output_content="out",
    )
    db_session.add(trace)
    db_session.commit()
    return trace.trace_id


@pytest.fixture
def repo_env(client):
    """Yields (repo, db_session, created, client) and cleans up any
    tasks/traces created. Tasks are created and deleted via the API client;
    traces are inserted/removed directly since the client has no trace API."""
    db_session = override_get_db_session()
    repo = _build_repo(db_session)
    created = {"task_ids": [], "trace_ids": []}
    yield repo, db_session, created, client
    if created["trace_ids"]:
        db_session.query(DatabaseTraceMetadata).filter(
            DatabaseTraceMetadata.trace_id.in_(created["trace_ids"]),
        ).delete(synchronize_session=False)
        db_session.commit()
    for task_id in created["task_ids"]:
        client.delete_task(task_id)


@pytest.mark.unit_tests
def test_last_active_filter_includes_old_task_with_recent_trace(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    # Task created 30 days ago but with a trace that ended 1 day ago.
    old_task = _add_task(
        client,
        db_session,
        "old-but-active",
        created_at=now - timedelta(days=30),
    )
    trace = _add_trace(db_session, old_task, end_time=now - timedelta(days=1))
    created["task_ids"].append(old_task)
    created["trace_ids"].append(trace)

    tasks, count = repo.query_tasks(
        ids=[old_task],
        last_active_start_time=now - timedelta(days=7),
        page_size=None,
    )

    assert count == 1
    assert [t.id for t in tasks] == [old_task]


@pytest.mark.unit_tests
def test_last_active_filter_excludes_only_old_or_traceless_tasks(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    recent_task = _add_task(
        client,
        db_session,
        "recent",
        created_at=now - timedelta(days=30),
    )
    recent_trace = _add_trace(db_session, recent_task, end_time=now - timedelta(days=2))

    stale_task = _add_task(
        client,
        db_session,
        "stale",
        created_at=now - timedelta(days=30),
    )
    stale_trace = _add_trace(db_session, stale_task, end_time=now - timedelta(days=60))

    traceless_task = _add_task(
        client,
        db_session,
        "traceless",
        created_at=now - timedelta(days=1),
    )

    created["task_ids"] += [recent_task, stale_task, traceless_task]
    created["trace_ids"] += [recent_trace, stale_trace]

    tasks, count = repo.query_tasks(
        ids=[recent_task, stale_task, traceless_task],
        last_active_start_time=now - timedelta(days=7),
        page_size=None,
    )

    # Only the task with a trace inside the window survives the INNER join.
    assert count == 1
    assert [t.id for t in tasks] == [recent_task]


@pytest.mark.unit_tests
def test_no_filter_returns_all_including_traceless(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    active_task = _add_task(
        client,
        db_session,
        "active",
        created_at=now - timedelta(days=30),
    )
    active_trace = _add_trace(db_session, active_task, end_time=now - timedelta(days=1))
    traceless_task = _add_task(
        client,
        db_session,
        "traceless",
        created_at=now - timedelta(days=2),
    )

    created["task_ids"] += [active_task, traceless_task]
    created["trace_ids"].append(active_trace)

    tasks, count = repo.query_tasks(
        ids=[active_task, traceless_task],
        page_size=None,
    )

    # No filter => no join => trace-less tasks are still returned.
    assert count == 2
    assert set(t.id for t in tasks) == {active_task, traceless_task}


@pytest.mark.unit_tests
def test_last_active_end_time_bound(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    recent_task = _add_task(
        client,
        db_session,
        "recent",
        created_at=now - timedelta(days=30),
    )
    recent_trace = _add_trace(
        db_session,
        recent_task,
        end_time=now - timedelta(hours=1),
    )
    old_task = _add_task(client, db_session, "old", created_at=now - timedelta(days=30))
    old_trace = _add_trace(db_session, old_task, end_time=now - timedelta(days=20))

    created["task_ids"] += [recent_task, old_task]
    created["trace_ids"] += [recent_trace, old_trace]

    # Only activity on or before 10 days ago.
    tasks, count = repo.query_tasks(
        ids=[recent_task, old_task],
        last_active_end_time=now - timedelta(days=10),
        page_size=None,
    )

    assert count == 1
    assert [t.id for t in tasks] == [old_task]


@pytest.mark.unit_tests
def test_default_sort_matches_created_at_desc(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    first = _add_task(client, db_session, "a-first", created_at=now - timedelta(days=3))
    second = _add_task(
        client,
        db_session,
        "b-second",
        created_at=now - timedelta(days=2),
    )
    third = _add_task(client, db_session, "c-third", created_at=now - timedelta(days=1))
    created["task_ids"] += [first, second, third]

    ids = [first, second, third]

    # No sort_field: preserves historical created_at DESC default.
    tasks, _ = repo.query_tasks(ids=ids, page_size=None)
    assert [t.id for t in tasks] == [third, second, first]

    tasks_asc, _ = repo.query_tasks(
        ids=ids,
        sort=PaginationSortMethod.ASCENDING,
        page_size=None,
    )
    assert [t.id for t in tasks_asc] == [first, second, third]


@pytest.mark.unit_tests
def test_sort_by_name(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    # created_at order is deliberately the reverse of alphabetical name order.
    charlie = _add_task(
        client,
        db_session,
        "charlie",
        created_at=now - timedelta(days=1),
    )
    bravo = _add_task(client, db_session, "bravo", created_at=now - timedelta(days=2))
    alpha = _add_task(client, db_session, "alpha", created_at=now - timedelta(days=3))
    created["task_ids"] += [charlie, bravo, alpha]

    ids = [charlie, bravo, alpha]

    tasks_asc, _ = repo.query_tasks(
        ids=ids,
        sort_field=TaskSortField.NAME,
        sort=PaginationSortMethod.ASCENDING,
        page_size=None,
    )
    assert [t.name for t in tasks_asc] == ["alpha", "bravo", "charlie"]

    tasks_desc, _ = repo.query_tasks(
        ids=ids,
        sort_field=TaskSortField.NAME,
        sort=PaginationSortMethod.DESCENDING,
        page_size=None,
    )
    assert [t.name for t in tasks_desc] == ["charlie", "bravo", "alpha"]


@pytest.mark.unit_tests
def test_sort_by_updated_at(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    a = _add_task(
        client,
        db_session,
        "a",
        created_at=now - timedelta(days=10),
        updated_at=now - timedelta(days=1),
    )
    b = _add_task(
        client,
        db_session,
        "b",
        created_at=now - timedelta(days=9),
        updated_at=now - timedelta(days=5),
    )
    created["task_ids"] += [a, b]
    ids = [a, b]

    tasks_desc, _ = repo.query_tasks(
        ids=ids,
        sort_field=TaskSortField.UPDATED_AT,
        sort=PaginationSortMethod.DESCENDING,
        page_size=None,
    )
    assert [t.id for t in tasks_desc] == [a, b]

    tasks_asc, _ = repo.query_tasks(
        ids=ids,
        sort_field=TaskSortField.UPDATED_AT,
        sort=PaginationSortMethod.ASCENDING,
        page_size=None,
    )
    assert [t.id for t in tasks_asc] == [b, a]


@pytest.mark.unit_tests
def test_sort_by_last_active_nulls_last(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()

    recent = _add_task(client, db_session, "recent", created_at=now - timedelta(days=5))
    recent_trace = _add_trace(db_session, recent, end_time=now - timedelta(days=1))
    older = _add_task(client, db_session, "older", created_at=now - timedelta(days=5))
    older_trace = _add_trace(db_session, older, end_time=now - timedelta(days=10))
    traceless = _add_task(
        client,
        db_session,
        "traceless",
        created_at=now - timedelta(days=5),
    )

    created["task_ids"] += [recent, older, traceless]
    created["trace_ids"] += [recent_trace, older_trace]

    ids = [recent, older, traceless]

    # DESC: most-recently-active first, trace-less (NULL) pushed to the end.
    tasks_desc, count = repo.query_tasks(
        ids=ids,
        sort_field=TaskSortField.LAST_ACTIVE,
        sort=PaginationSortMethod.DESCENDING,
        page_size=None,
    )
    assert count == 3
    assert [t.id for t in tasks_desc] == [recent, older, traceless]

    # ASC: oldest activity first, trace-less (NULL) still last.
    tasks_asc, _ = repo.query_tasks(
        ids=ids,
        sort_field=TaskSortField.LAST_ACTIVE,
        sort=PaginationSortMethod.ASCENDING,
        page_size=None,
    )
    assert [t.id for t in tasks_asc] == [older, recent, traceless]


@pytest.mark.unit_tests
def test_last_active_filter_respects_org_scope(repo_env):
    repo, db_session, created, client = repo_env
    now = datetime.now()
    other_org = uuid.uuid4()

    task = _add_task(client, db_session, "scoped", created_at=now - timedelta(days=30))
    # Trace belongs to a DIFFERENT org than the query scope.
    trace = _add_trace(
        db_session,
        task,
        end_time=now - timedelta(days=1),
        org_id=other_org,
    )
    created["task_ids"].append(task)
    created["trace_ids"].append(trace)

    # Scoped to DEFAULT_ORG_ID: the other-org trace must not count toward
    # last_active, so the INNER join drops the task.
    tasks, count = repo.query_tasks(
        ids=[task],
        last_active_start_time=now - timedelta(days=7),
        org_scope=DEFAULT_ORG_ID,
        page_size=None,
    )
    assert count == 0
    assert tasks == []


# --- _get_task_creation_source: service names reach every category (UP-4974) -------
#
# These call the method off an uninitialised instance. It touches no `self`, so a
# real TaskRepository would mean a DB session, a rules repo, a metrics repo and an
# application config for a pure mapping -- a fixture cost that buys nothing and
# hides which input produced which output.


def _task_carrying(creation_source, service_names):
    """A task holding one creation source, with query-time service names attached."""
    now = datetime.now()
    return Task(
        id=str(uuid.uuid4()),
        name="agent-task",
        created_at=now,
        updated_at=now,
        org_id=uuid.uuid4(),
        task_metadata=TaskMetadata(
            creation_source=AgentCreationSource(root=creation_source),
        ),
        service_names=service_names,
    )


def _resolve(creation_source, service_names):
    repo = TaskRepository.__new__(TaskRepository)
    return repo._get_task_creation_source(
        _task_carrying(creation_source, service_names),
    )


DISCOVERY_SOURCES = [
    pytest.param(
        CloudAgentCreationSource(
            vendor="aws_bedrock",
            address=SourceAddress(
                instance="111122223333",
                resource_id="AGENT1",
                scope="us-east-1",
            ),
        ),
        id="CLOUD",
    ),
    pytest.param(
        SIEMAgentCreationSource(
            vendor="splunk_es",
            address=SourceAddress(instance="splunk-prod", resource_id="rec-1"),
        ),
        id="SIEM",
    ),
    pytest.param(
        EndpointAgentCreationSource(
            vendor="jamf_pro",
            address=SourceAddress(instance="serial:X", resource_id="openclaw"),
        ),
        id="ENDPOINT",
    ),
]


@pytest.mark.unit_tests
@pytest.mark.parametrize("creation_source", DISCOVERY_SOURCES)
def test_discovery_categories_receive_service_names(creation_source):
    """The discovery categories nest service names under observations.

    Every category needs its own case rather than one representative: the bug this
    replaces dropped the names for whichever variants the isinstance chain did not
    name, so a sample would reproduce exactly that blind spot.
    """
    resolved = _resolve(creation_source, ["svc-a", "svc-b"])

    assert resolved is not None
    assert resolved.root.observations.service_names == ["svc-a", "svc-b"]


@pytest.mark.unit_tests
@pytest.mark.parametrize("creation_source", DISCOVERY_SOURCES)
def test_injecting_service_names_changes_nothing_else(creation_source):
    """Identity has to survive the copy, or the task resolves to the wrong agent."""
    resolved = _resolve(creation_source, ["svc-a"])

    assert resolved.root.type == creation_source.type
    assert resolved.root.vendor == creation_source.vendor
    assert resolved.root.address == creation_source.address


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "creation_source",
    [
        pytest.param(
            GCPAgentCreationSource(
                gcp_project_id="p",
                gcp_region="us-central1",
                gcp_reasoning_engine_id="e",
            ),
            id="GCP",
        ),
        pytest.param(OTELAgentCreationSource(), id="OTEL"),
    ],
)
def test_pre_category_variants_still_use_the_flat_field(creation_source):
    """Regression guard: widening the dispatch must not move these.

    Their service_names is a flat field, deprecated but still the only one the
    existing task-resolution path reads.
    """
    resolved = _resolve(creation_source, ["svc-a"])

    assert resolved.root.service_names == ["svc-a"]


@pytest.mark.unit_tests
def test_a_manual_source_gains_nothing():
    """MANUAL records a human decision, not an observation, so it has nowhere to put
    service names and must pass through untouched."""
    source = ManualAgentCreationSource()

    resolved = _resolve(source, ["svc-a"])

    assert resolved.root == source
