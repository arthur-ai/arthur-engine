"""Repository coverage check (UP-4432, stretch goal).

Asserts that the resource-id fetch methods on task-scoped repositories
accept an `org_scope` keyword parameter — the Pattern C contract from
design doc §7. A missing `org_scope` arg means the method can return a
cross-org row to a tenant caller because the handler can't filter at the
DB layer.

This is a hand-maintained inclusion list. An auto-scan with exclusions
was prototyped and surfaced ~14 genuine Pattern C gaps in repositories
not covered by UP-4429 (metrics, rules, trace transforms, experiment
test cases). Those are a follow-up; keeping the inclusion list here so
this PR ships the test infra without scope creep. Track via:

    https://arthurai.atlassian.net/browse/UP-4429

The ticket explicitly permits dropping this if introspection gets
brittle. Start with the most-touched repositories and grow the list as
new Pattern C surface is added.
"""

import inspect

import pytest

from repositories.agentic_experiment_repository import AgenticExperimentRepository
from repositories.agentic_notebook_repository import AgenticNotebookRepository
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from repositories.datasets_repository import DatasetRepository
from repositories.inference_repository import InferenceRepository
from repositories.span_repository import SpanRepository

# (repository class, method name). Cover the highest-touch resource-id
# fetch methods. New Pattern C surface should be added here.
TASK_SCOPED_FETCHERS: list[tuple[type, str]] = [
    (InferenceRepository, "get_inference"),
    (SpanRepository, "get_trace_by_id"),
    (SpanRepository, "get_span_by_id"),
    (SpanRepository, "get_session_traces"),
    (SpanRepository, "get_annotation_by_id"),
    (DatasetRepository, "_get_db_dataset"),
    (DatasetRepository, "get_dataset"),
    (AgenticExperimentRepository, "get_experiment"),
    (AgenticNotebookRepository, "get_notebook"),
    (ContinuousEvalsRepository, "get_continuous_eval_by_id"),
]


def _has_org_scope_param(cls: type, method_name: str) -> tuple[bool, str]:
    """Returns (exists_with_org_scope, reason)."""
    method = getattr(cls, method_name, None)
    if method is None:
        return False, f"{cls.__name__}.{method_name} not found"
    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError) as exc:
        return False, f"signature inspect failed: {exc}"
    if "org_scope" not in sig.parameters:
        return False, "org_scope kwarg missing"
    return True, ""


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "cls, method_name",
    TASK_SCOPED_FETCHERS,
    ids=lambda v: v.__name__ if inspect.isclass(v) else v,
)
def test_repository_method_accepts_org_scope(cls: type, method_name: str):
    ok, reason = _has_org_scope_param(cls, method_name)
    assert ok, (
        f"{cls.__name__}.{method_name} must accept `org_scope: UUID | None` "
        f"for Pattern C tenant isolation (design §7). {reason}"
    )
