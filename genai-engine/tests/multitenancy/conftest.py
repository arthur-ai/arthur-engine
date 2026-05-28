"""Two-org fixture for the UP-4432 multi-tenant isolation suite.

Seeds the cross-org world described in design doc §12:

    O1 ──► T1a, T1b   (each with one inference + one feedback row)
    O2 ──► T2a, T2b   (each with one inference + one feedback row)
    system ──► T_sys  (already seeded by SystemTaskRepository on client init)

Mints tenant keys K1 (org=O1) and K2 (org=O2). The admin key carried by the
shared `GenaiEngineTestClientBase` plays the role of caller `A`.

Orgs/tasks/keys are created via the repository layer because the HTTP API
forces admin-created tasks into the `default` org (see design §8). Inference
+ feedback seeding uses the admin HTTP path so we exercise the real
validate_prompt/create_feedback code paths.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator, Optional

import pytest
from arthur_common.models.enums import APIKeysRolesEnum
from arthur_common.models.request_schemas import FeedbackRequest, NewTaskRequest

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.agentic_experiment_models import DatabaseAgenticExperiment
from db_models.dataset_models import DatabaseDatasetVersion
from db_models.task_models import DatabaseTask
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from dependencies import get_application_config
from repositories.api_key_repository import ApiKeyRepository
from repositories.metrics_repository import MetricRepository
from repositories.organizations_repository import OrganizationsRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.base_experiment_schemas import ExperimentStatus
from schemas.internal_schemas import Task
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.clients.unit_test_client import get_genai_engine_test_client


@dataclass(frozen=True)
class TaskRow:
    id: str
    name: str
    org_id: uuid.UUID
    inference_id: Optional[str]
    feedback_id: Optional[str]


@dataclass(frozen=True)
class TenantWorld:
    """Everything a multitenancy test needs to fire cross-org calls.

    `client` is the shared admin-authed test client (acts as caller `A`).
    `k1` / `k2` are raw bearer tokens for tenant keys scoped to O1 / O2.

    `t2a_*` fields are foreign Pattern C resources seeded under T2a in O2.
    Any of them may be None if seeding for that resource failed (the
    fixture is best-effort; individual tests skip when their target is
    missing).
    """

    client: GenaiEngineTestClientBase
    o1_id: uuid.UUID
    o2_id: uuid.UUID
    t1a: TaskRow
    t1b: TaskRow
    t2a: TaskRow
    t2b: TaskRow
    system_task_id: Optional[str]
    k1: str
    k2: str
    t2a_trace_id: Optional[str] = None
    t2a_annotation_id: Optional[str] = None
    t2a_dataset_id: Optional[str] = None
    t2a_experiment_id: Optional[str] = None

    @property
    def admin_headers(self) -> dict:
        return self.client.authorized_user_api_key_headers

    def headers_for(self, key: str) -> dict:
        return {"Authorization": f"Bearer {key}"}


def _short() -> str:
    return uuid.uuid4().hex[:8]


def _make_task(tasks_repo: TaskRepository, name: str, org_id: uuid.UUID) -> Task:
    request = NewTaskRequest(name=name)
    task = Task._from_request_model(request, org_id=org_id)
    # with_default_rules=False keeps the fixture light — isolation tests don't
    # depend on default rules being attached.
    return tasks_repo.create_task(task, with_default_rules=False)


def _seed_inference(
    client: GenaiEngineTestClientBase, task_id: str, label: str
) -> Optional[str]:
    """Seed one inference on `task_id` via the admin validate_prompt path.

    Returns the inference_id or None if the seed call failed (tests that
    require an inference will skip).
    """
    resp = client.base_client.post(
        f"/api/v2/tasks/{task_id}/validate_prompt",
        json={
            "prompt": f"hello {label}",
            "user_id": "mt-seed",
            "conversation_id": f"cv-{label}",
        },
        headers=client.authorized_user_api_key_headers,
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("inference_id")


def _seed_feedback(
    client: GenaiEngineTestClientBase, inference_id: str
) -> Optional[str]:
    resp = client.base_client.post(
        f"/api/v2/feedback/{inference_id}",
        json=FeedbackRequest(
            target="response_results",
            score=1,
            reason="mt-seed",
        ).model_dump(),
        headers=client.authorized_user_api_key_headers,
    )
    # Route returns 201 CREATED on success.
    if resp.status_code not in (200, 201):
        return None
    body = resp.json()
    return body.get("id") if isinstance(body, dict) else None


def _seed_trace(db, task_id: str, org_id: uuid.UUID) -> Optional[str]:
    """Insert a minimal trace + span row directly so K1 has a foreign trace_id
    to target. Returns the trace_id or None on failure."""
    try:
        now = datetime.now(timezone.utc)
        trace_id = uuid.uuid4().hex
        db.add(
            DatabaseTraceMetadata(
                trace_id=trace_id,
                task_id=task_id,
                org_id=org_id,
                start_time=now,
                end_time=now,
                span_count=1,
            )
        )
        db.add(
            DatabaseSpan(
                id=uuid.uuid4().hex,
                trace_id=trace_id,
                span_id=uuid.uuid4().hex,
                start_time=now,
                end_time=now,
                task_id=task_id,
                org_id=org_id,
                raw_data={},
                status_code="Unset",
            )
        )
        db.commit()
        return trace_id
    except Exception:
        db.rollback()
        return None


def _seed_annotation(db, trace_id: str, org_id: uuid.UUID) -> Optional[str]:
    """Annotate a foreign trace directly. Returns annotation_id or None."""
    try:
        annotation = DatabaseAgenticAnnotation(
            id=uuid.uuid4(),
            annotation_type="human",
            trace_id=trace_id,
            annotation_score=1,
            annotation_description="mt-seed",
            org_id=org_id,
        )
        db.add(annotation)
        db.commit()
        return str(annotation.id)
    except Exception:
        db.rollback()
        return None


def _seed_dataset(client: GenaiEngineTestClientBase, task_id: str) -> Optional[str]:
    """Admin POST /api/v2/tasks/{task_id}/datasets. Admin path bypasses
    org-scope so the dataset lands on T2a (which is in O2)."""
    resp = client.base_client.post(
        f"/api/v2/tasks/{task_id}/datasets",
        json={"name": f"mt-ds-{_short()}", "description": "mt-seed"},
        headers=client.authorized_user_api_key_headers,
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("id")


def _seed_experiment(db, task_id: str, dataset_id: str) -> Optional[str]:
    """Insert minimal DatasetVersion + AgenticExperiment rows so K1 has a
    foreign experiment_id to target. Returns experiment_id or None.
    Skipped if the dataset seed failed upstream."""
    if dataset_id is None:
        return None
    try:
        db.add(
            DatabaseDatasetVersion(
                version_number=1,
                dataset_id=uuid.UUID(dataset_id),
                column_names=[],
            )
        )
        db.flush()  # surface FK problems before adding the experiment

        experiment_id = uuid.uuid4().hex
        db.add(
            DatabaseAgenticExperiment(
                id=experiment_id,
                task_id=task_id,
                name=f"mt-exp-{_short()}",
                description="mt-seed",
                status=ExperimentStatus.QUEUED,
                http_template={},
                template_variable_mapping=[],
                dataset_id=uuid.UUID(dataset_id),
                dataset_version=1,
                eval_configs=[],
                total_rows=0,
                completed_rows=0,
                failed_rows=0,
            )
        )
        db.commit()
        return experiment_id
    except Exception:
        db.rollback()
        return None


@pytest.fixture(scope="module")
def client() -> Generator[GenaiEngineTestClientBase, None, None]:
    yield get_genai_engine_test_client()


@pytest.fixture(scope="module")
def tenant_world(
    client: GenaiEngineTestClientBase,
) -> Generator[TenantWorld, None, None]:
    db = override_get_db_session()
    app_config = get_application_config(session=db)
    rules_repo = RuleRepository(db)
    metric_repo = MetricRepository(db)
    tasks_repo = TaskRepository(db, rules_repo, metric_repo, app_config)
    orgs_repo = OrganizationsRepository(db)
    keys_repo = ApiKeyRepository(db)

    suffix = _short()
    o1 = orgs_repo.create_organization(name=f"test-mt-o1-{suffix}")
    o2 = orgs_repo.create_organization(name=f"test-mt-o2-{suffix}")

    t1a_t = _make_task(tasks_repo, f"mt-t1a-{suffix}", o1.id)
    t1b_t = _make_task(tasks_repo, f"mt-t1b-{suffix}", o1.id)
    t2a_t = _make_task(tasks_repo, f"mt-t2a-{suffix}", o2.id)
    t2b_t = _make_task(tasks_repo, f"mt-t2b-{suffix}", o2.id)

    k1 = keys_repo.create_api_key(
        description=f"mt-K1-{suffix}",
        roles=[APIKeysRolesEnum.TENANT_USER],
        org_id=o1.id,
    )
    k2 = keys_repo.create_api_key(
        description=f"mt-K2-{suffix}",
        roles=[APIKeysRolesEnum.TENANT_USER],
        org_id=o2.id,
    )

    rows = {}
    for task in (t1a_t, t1b_t, t2a_t, t2b_t):
        inf_id = _seed_inference(client, task.id, task.name)
        fb_id = _seed_feedback(client, inf_id) if inf_id else None
        rows[task.id] = TaskRow(
            id=task.id,
            name=task.name,
            org_id=task.org_id,
            inference_id=inf_id,
            feedback_id=fb_id,
        )

    # Pick any pre-seeded system task for the system-org-isolation test.
    # `tasks_repo.query_tasks(org_scope=…)` stringifies its UUID, which a
    # recent SQLAlchemy refused to bind to the UUID-typed `org_id` column.
    # Query the table directly via the is_system_task flag instead.
    db.expire_all()
    system_task_id: Optional[str] = None
    try:
        row = (
            db.query(DatabaseTask)
            .filter(DatabaseTask.is_system_task == True)  # noqa: E712
            .first()
        )
        if row is not None:
            system_task_id = str(row.id)
    except Exception:
        system_task_id = None

    # Foreign Pattern C resources under T2a (org=O2). Best-effort — tests
    # skip when their target is None.
    t2a_trace_id = _seed_trace(db, t2a_t.id, o2.id)
    t2a_annotation_id = (
        _seed_annotation(db, t2a_trace_id, o2.id) if t2a_trace_id else None
    )
    t2a_dataset_id = _seed_dataset(client, t2a_t.id)
    t2a_experiment_id = _seed_experiment(db, t2a_t.id, t2a_dataset_id)

    world = TenantWorld(
        client=client,
        o1_id=o1.id,
        o2_id=o2.id,
        t1a=rows[t1a_t.id],
        t1b=rows[t1b_t.id],
        t2a=rows[t2a_t.id],
        t2b=rows[t2b_t.id],
        system_task_id=system_task_id,
        k1=k1.key,
        k2=k2.key,
        t2a_trace_id=t2a_trace_id,
        t2a_annotation_id=t2a_annotation_id,
        t2a_dataset_id=t2a_dataset_id,
        t2a_experiment_id=t2a_experiment_id,
    )

    yield world

    # Best-effort cleanup. UUIDs in names avoid collisions if cleanup fails.
    for tid in [t1a_t.id, t1b_t.id, t2a_t.id, t2b_t.id]:
        try:
            tasks_repo.delete_task(task_id=tid)
        except Exception:
            pass
    db.close()
