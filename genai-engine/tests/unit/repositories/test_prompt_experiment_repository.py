from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from repositories.prompt_experiment_repository import PromptExperimentRepository
from schemas.base_experiment_schemas import TestCaseStatus

# Duck-typed stand-ins for the ORM/Pydantic inputs the repository reads.


def _make_dataset_row(row_id: str, context_value: str) -> Any:
    return SimpleNamespace(
        id=row_id,
        data={"context": context_value, "question": f"q-{row_id}"},
    )


def _make_dataset_ref() -> Any:
    return SimpleNamespace(id="ds-1", version=1)


def _make_prompt_variable_mapping() -> Any:
    return SimpleNamespace(
        variable_name="question",
        source=SimpleNamespace(
            dataset_column=SimpleNamespace(name="question"),
        ),
    )


def _make_prompt_config(name: str) -> Any:
    return SimpleNamespace(type="saved", name=name, version=1)


def _make_fake_get_db_test_cases(
    test_cases: list[Any],
    pages_requested: list[tuple[Optional[int], Optional[int]]],
) -> Any:
    """Build a stand-in for ``_get_db_test_cases`` that serves ``test_cases`` in
    pages, enforcing the streaming contract and recording each page requested."""

    def fake_get_db_test_cases(
        experiment_id: str,
        status: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        defer_eval_input_variables: bool = False,
    ) -> list[Any]:
        assert status == TestCaseStatus.COMPLETED.value
        assert defer_eval_input_variables is True
        assert offset is not None and limit is not None
        pages_requested.append((offset, limit))
        return test_cases[offset : offset + limit]

    return fake_get_db_test_cases


def _make_eval_config(eval_name: str) -> tuple[Any, Any]:
    eval_ref = SimpleNamespace(
        variable_mapping=[
            SimpleNamespace(
                variable_name="context",
                source=SimpleNamespace(
                    type="dataset_column",
                    dataset_column=SimpleNamespace(name="context"),
                ),
            ),
            SimpleNamespace(
                variable_name="response",
                source=SimpleNamespace(type="experiment_output"),
            ),
        ],
    )
    llm_eval = SimpleNamespace(name=eval_name, version=1)
    return eval_ref, llm_eval


@pytest.mark.unit_tests
def test_create_test_cases_flushes_per_row_and_bounds_peak() -> None:
    """The create path flushes and expunges each row's objects before the next,
    bounding peak memory to a single row."""
    num_rows = 3
    prompt_configs = [_make_prompt_config("p1"), _make_prompt_config("p2")]
    eval_configs = [_make_eval_config(f"eval-{i}") for i in range(4)]
    num_prompts = len(prompt_configs)
    num_evals = len(eval_configs)

    # One test case + (one prompt result + num_evals eval scores) per prompt.
    objects_per_row = 1 + num_prompts + (num_prompts * num_evals)

    dataset_rows = [
        _make_dataset_row(f"row-{i}", context_value="x" * 1000) for i in range(num_rows)
    ]

    # Track add / flush / expunge ordering to compute the live-object peak.
    events: list[str] = []
    db_session = MagicMock()
    db_session.query.return_value.filter.return_value.all.return_value = dataset_rows
    db_session.add.side_effect = lambda obj: events.append("add")
    db_session.flush.side_effect = lambda: events.append("flush")
    db_session.expunge.side_effect = lambda obj: events.append("expunge")

    repo = PromptExperimentRepository(db_session)

    total_rows = repo._create_test_cases_for_dataset(
        experiment_id="exp-1",
        dataset_ref=_make_dataset_ref(),
        prompt_variable_mappings=[_make_prompt_variable_mapping()],
        prompt_configs=prompt_configs,
        eval_configs=eval_configs,
        dataset_row_filter=None,
    )

    assert total_rows == num_rows

    # Flush once per row, and every created object is expunged.
    assert db_session.flush.call_count == num_rows
    assert db_session.add.call_count == num_rows * objects_per_row
    assert db_session.expunge.call_count == num_rows * objects_per_row

    # Peak live objects never exceeds a single row's worth.
    live = 0
    peak = 0
    for event in events:
        if event == "add":
            live += 1
            peak = max(peak, live)
        elif event == "expunge":
            live -= 1
    assert peak == objects_per_row
    assert live == 0


@pytest.mark.unit_tests
def test_iter_completed_test_cases_streams_in_pages_and_releases_each() -> None:
    """Summary aggregation streams COMPLETED test cases page by page, expunging
    each page before loading the next, bounding peak memory to one page."""
    batch_size = 2
    num_test_cases = 5
    test_cases = [SimpleNamespace(id=f"tc-{i}") for i in range(num_test_cases)]

    # Ordered stream of yields and expunges, replayed to compute the live-object peak.
    events: list[tuple[str, str]] = []
    db_session = MagicMock()
    db_session.expunge.side_effect = lambda obj: events.append(("expunge", obj.id))

    repo = PromptExperimentRepository(db_session)

    # Serve pages via _get_db_test_cases, enforcing the streaming contract.
    pages_requested: list[tuple[Optional[int], Optional[int]]] = []

    repo._get_db_test_cases = _make_fake_get_db_test_cases(  # type: ignore[method-assign]
        test_cases,
        pages_requested,
    )

    yielded: list[str] = []
    for test_case in repo.iter_completed_test_cases_for_summary(
        "exp-1",
        batch_size=batch_size,
    ):
        yielded.append(test_case.id)
        events.append(("yield", test_case.id))

    # Every test case is yielded exactly once, in order.
    assert yielded == [tc.id for tc in test_cases]

    # Every yielded test case is expunged exactly once.
    expunged = sorted(obj_id for kind, obj_id in events if kind == "expunge")
    assert expunged == sorted(tc.id for tc in test_cases)

    # Paging advances by batch_size and stops on the first empty page.
    assert pages_requested == [(0, 2), (2, 2), (4, 2), (6, 2)]

    # Peak live (yielded-but-not-yet-expunged) objects never exceeds one page.
    live = 0
    peak = 0
    for kind, _obj_id in events:
        if kind == "yield":
            live += 1
            peak = max(peak, live)
        else:
            live -= 1
    assert peak == batch_size
    assert peak < num_test_cases
    assert live == 0
