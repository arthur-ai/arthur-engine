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
from typing import Generator, Optional

import pytest
from arthur_common.models.enums import APIKeysRolesEnum
from arthur_common.models.request_schemas import FeedbackRequest, NewTaskRequest

from dependencies import get_application_config
from repositories.api_key_repository import ApiKeyRepository
from repositories.metrics_repository import MetricRepository
from repositories.organizations_repository import OrganizationsRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.internal_schemas import Task
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.clients.unit_test_client import get_genai_engine_test_client
from utils.constants import SYSTEM_ORG_ID


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
            target="context_relevance",
            score=1,
            reason="mt-seed",
        ).model_dump(),
        headers=client.authorized_user_api_key_headers,
    )
    if resp.status_code != 200:
        return None
    body = resp.json()
    return body.get("id") if isinstance(body, dict) else None


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
    db.expire_all()
    system_task_row = next(
        iter(tasks_repo.query_tasks(org_scope=SYSTEM_ORG_ID, page_size=1)[0]),
        None,
    )
    system_task_id = str(system_task_row.id) if system_task_row else None

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
    )

    yield world

    # Best-effort cleanup. UUIDs in names avoid collisions if cleanup fails.
    for tid in [t1a_t.id, t1b_t.id, t2a_t.id, t2b_t.id]:
        try:
            tasks_repo.delete_task(task_id=tid)
        except Exception:
            pass
    db.close()
