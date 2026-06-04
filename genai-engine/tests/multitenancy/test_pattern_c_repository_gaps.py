"""Repository-level Pattern C tests for UP-4470 (1-hop gap methods only).

UP-4470 audited 14 task-scoped fetch methods missing `org_scope`. Only the
methods whose org isolation is a **1-hop** check (parent → tasks.org_id) are
closed in this PR:

* ``RuleRepository.get_rule_by_id`` — rule fetched by PK, then a 1-hop
  tasks_to_rules → tasks existence check (DEFAULT-scope rules pass through).
* ``TraceTransformRepository.get_transform_dependents`` — gates on the parent
  transform's ownership (transform → tasks.org_id, 1-hop).

The other 12 methods (metrics, trace-transform versions, experiment test
cases) need a 2-hop join to reach ``tasks.org_id`` and are deferred — see the
UP-4470 ticket. These tests assert the uniform contract for the closed
methods:

    org_scope=O2 (foreign)  -> hidden (404 / empty)
    org_scope=None (admin)  -> visible
    org_scope=O1 (owner)    -> visible
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Generator

import pytest
from arthur_common.models.enums import RuleScope, RuleType
from fastapi import HTTPException

from db_models.llm_eval_models import DatabaseContinuousEval, DatabaseLLMEval
from db_models.rule_models import DatabaseRule
from db_models.task_models import DatabaseTask, DatabaseTaskToRules
from db_models.transform_models import (
    DatabaseTraceTransform,
    DatabaseTraceTransformVersion,
)
from repositories.organizations_repository import OrganizationsRepository
from repositories.rules_repository import RuleRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.enums import RuleScoringMethod
from tests.clients.base_test_client import override_get_db_session


def _short() -> str:
    return uuid.uuid4().hex[:8]


@dataclass(frozen=True)
class GapWorld:
    """Two-org world: O1 owns a task-scoped rule and a transform; a DEFAULT
    rule is owned by no task."""

    o1_id: uuid.UUID
    o2_id: uuid.UUID
    t1_id: str
    t2_id: str
    task_rule_id: str
    default_rule_id: str
    transform_id: uuid.UUID


def _make_task(db, name: str, org_id: uuid.UUID) -> str:
    now = datetime.now()
    task_id = uuid.uuid4().hex
    db.add(
        DatabaseTask(
            id=task_id,
            name=name,
            created_at=now,
            updated_at=now,
            org_id=org_id,
        ),
    )
    db.flush()
    return task_id


def _seed_rule(db, scope: RuleScope, task_id: str | None) -> str:
    now = datetime.now()
    rule_id = str(uuid.uuid4())
    db.add(
        DatabaseRule(
            id=rule_id,
            name=f"gap-rule-{_short()}",
            type=RuleType.KEYWORD.value,
            created_at=now,
            updated_at=now,
            prompt_enabled=True,
            response_enabled=True,
            scoring_method=RuleScoringMethod.BINARY.value,
            scope=scope.value,
            archived=False,
        ),
    )
    db.flush()
    if task_id is not None:
        db.add(DatabaseTaskToRules(task_id=task_id, rule_id=rule_id, enabled=True))
        db.flush()
    return rule_id


def _seed_transform_with_dependent(db, task_id: str) -> uuid.UUID:
    """Seed a transform + version on task_id, plus an llm_eval and a
    continuous_eval that depends on the transform (so get_transform_dependents
    has something to return for the owner)."""
    transform_id = uuid.uuid4()
    db.add(
        DatabaseTraceTransform(
            id=transform_id,
            task_id=task_id,
            name=f"gap-transform-{_short()}",
            description="up-4470",
        ),
    )
    db.flush()
    db.add(
        DatabaseTraceTransformVersion(
            id=uuid.uuid4(),
            transform_id=transform_id,
            version_number=1,
            definition={"variables": []},
        ),
    )
    db.flush()

    eval_name = f"gap-eval-{_short()}"
    db.add(
        DatabaseLLMEval(
            task_id=task_id,
            name=eval_name,
            version=1,
            model_name="gpt-4",
            model_provider="openai",
            instructions="up-4470",
            variables=[],
        ),
    )
    db.flush()
    db.add(
        DatabaseContinuousEval(
            id=uuid.uuid4(),
            name=f"gap-ceval-{_short()}",
            task_id=task_id,
            llm_eval_name=eval_name,
            llm_eval_version=1,
            transform_id=transform_id,
            transform_variable_mapping=[],
        ),
    )
    db.flush()
    return transform_id


@pytest.fixture(scope="module")
def gap_world() -> Generator[GapWorld, None, None]:
    db = override_get_db_session()
    orgs_repo = OrganizationsRepository(db)

    suffix = _short()
    o1 = orgs_repo.create_organization(name=f"gap-o1-{suffix}")
    o2 = orgs_repo.create_organization(name=f"gap-o2-{suffix}")

    t1_id = _make_task(db, f"gap-t1-{suffix}", o1.id)
    t2_id = _make_task(db, f"gap-t2-{suffix}", o2.id)

    task_rule_id = _seed_rule(db, RuleScope.TASK, t1_id)
    default_rule_id = _seed_rule(db, RuleScope.DEFAULT, None)
    transform_id = _seed_transform_with_dependent(db, t1_id)

    db.commit()

    world = GapWorld(
        o1_id=o1.id,
        o2_id=o2.id,
        t1_id=t1_id,
        t2_id=t2_id,
        task_rule_id=task_rule_id,
        default_rule_id=default_rule_id,
        transform_id=transform_id,
    )

    yield world

    # Best-effort cleanup; UUID-suffixed names avoid collisions if this fails.
    try:
        db.query(DatabaseContinuousEval).filter(
            DatabaseContinuousEval.task_id == t1_id,
        ).delete()
        db.query(DatabaseLLMEval).filter(DatabaseLLMEval.task_id == t1_id).delete()
        db.query(DatabaseTraceTransformVersion).filter(
            DatabaseTraceTransformVersion.transform_id == transform_id,
        ).delete()
        db.query(DatabaseTraceTransform).filter(
            DatabaseTraceTransform.id == transform_id,
        ).delete()
        db.query(DatabaseTaskToRules).filter(
            DatabaseTaskToRules.task_id == t1_id,
        ).delete()
        db.query(DatabaseRule).filter(
            DatabaseRule.id.in_([task_rule_id, default_rule_id]),
        ).delete(synchronize_session=False)
        db.query(DatabaseTask).filter(
            DatabaseTask.id.in_([t1_id, t2_id]),
        ).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    db.close()


# --------------------------------------------------------------------------- #
# rules_repository.get_rule_by_id (rule PK fetch + 1-hop tasks_to_rules → tasks)
# --------------------------------------------------------------------------- #


@pytest.mark.unit_tests
def test_get_rule_by_id_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = RuleRepository(db)

    assert repo.get_rule_by_id(gap_world.task_rule_id).id == gap_world.task_rule_id
    assert (
        repo.get_rule_by_id(gap_world.task_rule_id, org_scope=gap_world.o1_id).id
        == gap_world.task_rule_id
    )
    with pytest.raises(HTTPException) as exc:
        repo.get_rule_by_id(gap_world.task_rule_id, org_scope=gap_world.o2_id)
    assert exc.value.status_code == 404


@pytest.mark.unit_tests
def test_get_rule_by_id_default_rule_passthrough(gap_world: GapWorld):
    """A DEFAULT-scope rule is visible under any org_scope (design §7)."""
    db = override_get_db_session()
    repo = RuleRepository(db)

    assert (
        repo.get_rule_by_id(gap_world.default_rule_id, org_scope=gap_world.o1_id).id
        == gap_world.default_rule_id
    )
    # Even an org that owns no link to it still sees the default rule.
    assert (
        repo.get_rule_by_id(gap_world.default_rule_id, org_scope=gap_world.o2_id).id
        == gap_world.default_rule_id
    )


# --------------------------------------------------------------------------- #
# trace_transform_repository.get_transform_dependents (1-hop transform gate)
# --------------------------------------------------------------------------- #


@pytest.mark.unit_tests
def test_get_transform_dependents_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = TraceTransformRepository(db)

    assert repo.get_transform_dependents(gap_world.transform_id).has_dependents
    assert repo.get_transform_dependents(
        gap_world.transform_id,
        org_scope=gap_world.o1_id,
    ).has_dependents
    # Cross-org sees no dependents rather than another org's resources.
    assert not repo.get_transform_dependents(
        gap_world.transform_id,
        org_scope=gap_world.o2_id,
    ).has_dependents
