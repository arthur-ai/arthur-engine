"""Repository-level Pattern C tests for UP-4470.

UP-4470 closes 14 task-scoped fetch methods that took a resource id but did
not accept `org_scope` — leaving tenant isolation enforced only at the route
layer (design doc §7, Pattern C). These tests exercise each method directly
against the data layer, asserting the uniform contract:

    org_scope=O2 (foreign)  -> None / [] / 404   (cross-org row is hidden)
    org_scope=None (admin)  -> row                (no filtering)
    org_scope=O1 (owner)    -> row                (own row passes through)

plus the rules special case: a `DEFAULT`-scope rule is visible under any
`org_scope`.

The fixture seeds a two-org world entirely through the repository/ORM layer
(the HTTP API forces admin-created tasks into the `default` org), with every
Pattern C resource family owned by O1's task `t1`.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Generator

import pytest
from arthur_common.models.enums import RuleScope, RuleType
from fastapi import HTTPException

from db_models.agentic_experiment_models import (
    DatabaseAgenticExperiment,
    DatabaseAgenticExperimentTestCase,
)
from db_models.llm_eval_models import DatabaseContinuousEval, DatabaseLLMEval
from db_models.prompt_experiment_models import (
    DatabasePromptExperiment,
    DatabasePromptExperimentTestCase,
)
from db_models.rag_experiment_models import (
    DatabaseRagExperiment,
    DatabaseRagExperimentTestCase,
)
from db_models.rule_models import DatabaseRule
from db_models.task_models import DatabaseTask, DatabaseTaskToRules
from db_models.telemetry_models import DatabaseMetric, DatabaseTaskToMetrics
from db_models.transform_models import (
    DatabaseTraceTransform,
    DatabaseTraceTransformVersion,
)
from repositories.agentic_experiment_repository import AgenticExperimentRepository
from repositories.metrics_repository import MetricRepository
from repositories.organizations_repository import OrganizationsRepository
from repositories.prompt_experiment_repository import PromptExperimentRepository
from repositories.rag_experiment_repository import RagExperimentRepository
from repositories.rules_repository import RuleRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.enums import RuleScoringMethod
from tests.clients.base_test_client import override_get_db_session


def _short() -> str:
    return uuid.uuid4().hex[:8]


@dataclass(frozen=True)
class GapWorld:
    """Two-org world with every Pattern C gap resource owned by O1's task."""

    o1_id: uuid.UUID
    o2_id: uuid.UUID
    t1_id: str
    t2_id: str
    metric_id: str
    task_rule_id: str
    default_rule_id: str
    transform_id: uuid.UUID
    version_id: uuid.UUID
    agentic_experiment_id: str
    agentic_test_case_id: str
    prompt_experiment_id: str
    prompt_test_case_id: str
    rag_experiment_id: str
    rag_test_case_id: str


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


def _seed_metric(db, task_id: str) -> str:
    now = datetime.now()
    metric_id = str(uuid.uuid4())
    db.add(
        DatabaseMetric(
            id=metric_id,
            created_at=now,
            updated_at=now,
            type="QueryRelevance",
            name=f"gap-metric-{_short()}",
            metric_metadata="up-4470",
            config=None,
        ),
    )
    db.flush()
    db.add(DatabaseTaskToMetrics(task_id=task_id, metric_id=metric_id, enabled=True))
    db.flush()
    return metric_id


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


def _seed_transform(db, task_id: str) -> tuple[uuid.UUID, uuid.UUID]:
    transform_id = uuid.uuid4()
    version_id = uuid.uuid4()
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
            id=version_id,
            transform_id=transform_id,
            version_number=1,
            definition={"variables": []},
        ),
    )
    db.flush()
    return transform_id, version_id


def _seed_transform_dependent(db, task_id: str, transform_id: uuid.UUID) -> None:
    """Seed an llm_eval + continuous_eval that depends on the transform so
    get_transform_dependents has something to return for the owner."""
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


def _seed_agentic(db, task_id: str) -> tuple[str, str]:
    experiment_id = uuid.uuid4().hex
    db.add(
        DatabaseAgenticExperiment(
            id=experiment_id,
            task_id=task_id,
            name=f"gap-agentic-{_short()}",
            description="up-4470",
            status="queued",
            http_template={},
            template_variable_mapping=[],
            dataset_id=uuid.uuid4(),
            dataset_version=1,
            eval_configs=[],
            total_rows=0,
            completed_rows=0,
            failed_rows=0,
        ),
    )
    db.flush()
    test_case_id = uuid.uuid4().hex
    db.add(
        DatabaseAgenticExperimentTestCase(
            id=test_case_id,
            status="completed",
            dataset_row_id="row-0",
            experiment_id=experiment_id,
            template_input_variables=[],
        ),
    )
    db.flush()
    return experiment_id, test_case_id


def _seed_prompt(db, task_id: str) -> tuple[str, str]:
    experiment_id = uuid.uuid4().hex
    db.add(
        DatabasePromptExperiment(
            id=experiment_id,
            task_id=task_id,
            name=f"gap-prompt-{_short()}",
            description="up-4470",
            status="queued",
            prompt_configs=[],
            prompt_variable_mapping=[],
            dataset_id=uuid.uuid4(),
            dataset_version=1,
            eval_configs=[],
            total_rows=0,
            completed_rows=0,
            failed_rows=0,
        ),
    )
    db.flush()
    test_case_id = uuid.uuid4().hex
    db.add(
        DatabasePromptExperimentTestCase(
            id=test_case_id,
            status="completed",
            dataset_row_id="row-0",
            experiment_id=experiment_id,
            prompt_input_variables=[],
        ),
    )
    db.flush()
    return experiment_id, test_case_id


def _seed_rag(db, task_id: str) -> tuple[str, str]:
    experiment_id = uuid.uuid4().hex
    db.add(
        DatabaseRagExperiment(
            id=experiment_id,
            task_id=task_id,
            name=f"gap-rag-{_short()}",
            description="up-4470",
            status="queued",
            rag_configs=[],
            dataset_id=uuid.uuid4(),
            dataset_version=1,
            eval_configs=[],
            total_rows=0,
            completed_rows=0,
            failed_rows=0,
        ),
    )
    db.flush()
    test_case_id = uuid.uuid4().hex
    db.add(
        DatabaseRagExperimentTestCase(
            id=test_case_id,
            status="completed",
            dataset_row_id="row-0",
            experiment_id=experiment_id,
        ),
    )
    db.flush()
    return experiment_id, test_case_id


@pytest.fixture(scope="module")
def gap_world() -> Generator[GapWorld, None, None]:
    db = override_get_db_session()
    orgs_repo = OrganizationsRepository(db)

    suffix = _short()
    o1 = orgs_repo.create_organization(name=f"gap-o1-{suffix}")
    o2 = orgs_repo.create_organization(name=f"gap-o2-{suffix}")

    t1_id = _make_task(db, f"gap-t1-{suffix}", o1.id)
    t2_id = _make_task(db, f"gap-t2-{suffix}", o2.id)

    metric_id = _seed_metric(db, t1_id)
    task_rule_id = _seed_rule(db, RuleScope.TASK, t1_id)
    default_rule_id = _seed_rule(db, RuleScope.DEFAULT, None)
    transform_id, version_id = _seed_transform(db, t1_id)
    _seed_transform_dependent(db, t1_id, transform_id)
    agentic_experiment_id, agentic_test_case_id = _seed_agentic(db, t1_id)
    prompt_experiment_id, prompt_test_case_id = _seed_prompt(db, t1_id)
    rag_experiment_id, rag_test_case_id = _seed_rag(db, t1_id)

    db.commit()

    world = GapWorld(
        o1_id=o1.id,
        o2_id=o2.id,
        t1_id=t1_id,
        t2_id=t2_id,
        metric_id=metric_id,
        task_rule_id=task_rule_id,
        default_rule_id=default_rule_id,
        transform_id=transform_id,
        version_id=version_id,
        agentic_experiment_id=agentic_experiment_id,
        agentic_test_case_id=agentic_test_case_id,
        prompt_experiment_id=prompt_experiment_id,
        prompt_test_case_id=prompt_test_case_id,
        rag_experiment_id=rag_experiment_id,
        rag_test_case_id=rag_test_case_id,
    )

    yield world

    # Best-effort cleanup; UUID-suffixed names avoid collisions if this fails.
    try:
        db.query(DatabaseContinuousEval).filter(
            DatabaseContinuousEval.task_id == t1_id,
        ).delete()
        db.query(DatabaseLLMEval).filter(DatabaseLLMEval.task_id == t1_id).delete()
        db.query(DatabaseAgenticExperimentTestCase).filter(
            DatabaseAgenticExperimentTestCase.experiment_id == agentic_experiment_id,
        ).delete()
        db.query(DatabasePromptExperimentTestCase).filter(
            DatabasePromptExperimentTestCase.experiment_id == prompt_experiment_id,
        ).delete()
        db.query(DatabaseRagExperimentTestCase).filter(
            DatabaseRagExperimentTestCase.experiment_id == rag_experiment_id,
        ).delete()
        db.query(DatabaseAgenticExperiment).filter(
            DatabaseAgenticExperiment.id == agentic_experiment_id,
        ).delete()
        db.query(DatabasePromptExperiment).filter(
            DatabasePromptExperiment.id == prompt_experiment_id,
        ).delete()
        db.query(DatabaseRagExperiment).filter(
            DatabaseRagExperiment.id == rag_experiment_id,
        ).delete()
        db.query(DatabaseTraceTransformVersion).filter(
            DatabaseTraceTransformVersion.transform_id == transform_id,
        ).delete()
        db.query(DatabaseTraceTransform).filter(
            DatabaseTraceTransform.id == transform_id,
        ).delete()
        db.query(DatabaseTaskToMetrics).filter(
            DatabaseTaskToMetrics.task_id == t1_id,
        ).delete()
        db.query(DatabaseMetric).filter(DatabaseMetric.id == metric_id).delete()
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
# metrics_repository
# --------------------------------------------------------------------------- #


@pytest.mark.unit_tests
def test_get_metric_by_id_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = MetricRepository(db)

    assert repo.get_metric_by_id(gap_world.metric_id) is not None
    assert (
        repo.get_metric_by_id(gap_world.metric_id, org_scope=gap_world.o1_id)
        is not None
    )
    with pytest.raises(ValueError):
        repo.get_metric_by_id(gap_world.metric_id, org_scope=gap_world.o2_id)


@pytest.mark.unit_tests
def test_get_metric_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = MetricRepository(db)

    assert repo.get_metric(gap_world.metric_id).id == gap_world.metric_id
    assert (
        repo.get_metric(gap_world.metric_id, org_scope=gap_world.o1_id).id
        == gap_world.metric_id
    )
    with pytest.raises(ValueError):
        repo.get_metric(gap_world.metric_id, org_scope=gap_world.o2_id)


@pytest.mark.unit_tests
def test_get_metrics_by_metric_id_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = MetricRepository(db)
    ids = [gap_world.metric_id]

    assert [m.id for m in repo.get_metrics_by_metric_id(ids)] == ids
    assert [
        m.id for m in repo.get_metrics_by_metric_id(ids, org_scope=gap_world.o1_id)
    ] == ids
    assert repo.get_metrics_by_metric_id(ids, org_scope=gap_world.o2_id) == []


# --------------------------------------------------------------------------- #
# rules_repository
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
# trace_transform_repository
# --------------------------------------------------------------------------- #


@pytest.mark.unit_tests
def test_get_latest_definition_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = TraceTransformRepository(db)

    assert repo.get_latest_definition(gap_world.transform_id) is not None
    assert (
        repo.get_latest_definition(gap_world.transform_id, org_scope=gap_world.o1_id)
        is not None
    )
    with pytest.raises(HTTPException) as exc:
        repo.get_latest_definition(gap_world.transform_id, org_scope=gap_world.o2_id)
    assert exc.value.status_code == 404


@pytest.mark.unit_tests
def test_list_versions_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = TraceTransformRepository(db)

    assert repo.list_versions(gap_world.transform_id).count == 1
    assert (
        repo.list_versions(gap_world.transform_id, org_scope=gap_world.o1_id).count == 1
    )
    # Cross-org returns an empty list, NOT a 404.
    assert (
        repo.list_versions(gap_world.transform_id, org_scope=gap_world.o2_id).count == 0
    )


@pytest.mark.unit_tests
def test_get_version_by_id_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = TraceTransformRepository(db)

    assert (
        repo.get_version_by_id(gap_world.transform_id, gap_world.version_id).id
        == gap_world.version_id
    )
    assert (
        repo.get_version_by_id(
            gap_world.transform_id,
            gap_world.version_id,
            org_scope=gap_world.o1_id,
        ).id
        == gap_world.version_id
    )
    with pytest.raises(HTTPException) as exc:
        repo.get_version_by_id(
            gap_world.transform_id,
            gap_world.version_id,
            org_scope=gap_world.o2_id,
        )
    assert exc.value.status_code == 404


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


# --------------------------------------------------------------------------- #
# experiment repositories (agentic / prompt / rag)
# --------------------------------------------------------------------------- #


@pytest.mark.unit_tests
def test_agentic_get_db_test_cases_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = AgenticExperimentRepository(db)
    exp_id = gap_world.agentic_experiment_id

    assert len(repo._get_db_test_cases(exp_id)) == 1
    assert len(repo._get_db_test_cases(exp_id, org_scope=gap_world.o1_id)) == 1
    assert repo._get_db_test_cases(exp_id, org_scope=gap_world.o2_id) == []


@pytest.mark.unit_tests
def test_agentic_get_db_test_case_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = AgenticExperimentRepository(db)
    tc_id = gap_world.agentic_test_case_id

    assert repo._get_db_test_case(tc_id) is not None
    assert repo._get_db_test_case(tc_id, org_scope=gap_world.o1_id) is not None
    assert repo._get_db_test_case(tc_id, org_scope=gap_world.o2_id) is None


@pytest.mark.unit_tests
def test_prompt_get_db_test_cases_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = PromptExperimentRepository(db)
    exp_id = gap_world.prompt_experiment_id

    assert len(repo._get_db_test_cases(exp_id)) == 1
    assert len(repo._get_db_test_cases(exp_id, org_scope=gap_world.o1_id)) == 1
    assert repo._get_db_test_cases(exp_id, org_scope=gap_world.o2_id) == []


@pytest.mark.unit_tests
def test_prompt_get_db_test_case_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = PromptExperimentRepository(db)
    tc_id = gap_world.prompt_test_case_id

    assert repo._get_db_test_case(tc_id) is not None
    assert repo._get_db_test_case(tc_id, org_scope=gap_world.o1_id) is not None
    assert repo._get_db_test_case(tc_id, org_scope=gap_world.o2_id) is None


@pytest.mark.unit_tests
def test_rag_get_db_test_cases_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = RagExperimentRepository(db)
    exp_id = gap_world.rag_experiment_id

    assert len(repo._get_db_test_cases(exp_id)) == 1
    assert len(repo._get_db_test_cases(exp_id, org_scope=gap_world.o1_id)) == 1
    assert repo._get_db_test_cases(exp_id, org_scope=gap_world.o2_id) == []


@pytest.mark.unit_tests
def test_rag_get_db_test_case_org_scope(gap_world: GapWorld):
    db = override_get_db_session()
    repo = RagExperimentRepository(db)
    tc_id = gap_world.rag_test_case_id

    assert repo._get_db_test_case(tc_id) is not None
    assert repo._get_db_test_case(tc_id, org_scope=gap_world.o1_id) is not None
    assert repo._get_db_test_case(tc_id, org_scope=gap_world.o2_id) is None
