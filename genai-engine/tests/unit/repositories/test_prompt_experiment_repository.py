from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from repositories.prompt_experiment_repository import PromptExperimentRepository
from schemas.base_experiment_schemas import TestCaseStatus

# These helpers return lightweight duck-typed stand-ins (SimpleNamespace) for
# the Pydantic/ORM inputs the repository reads attribute-by-attribute. They are
# annotated as Any so the calls stay type-clean without constructing the full
# real models, which would add heavy, unrelated setup to a memory-behavior test.


def _make_dataset_row(row_id: str, context_value: str) -> Any:
    """A stand-in for DatabaseDatasetVersionRow with the attributes the
    repository reads (.id and .data)."""
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


def _make_eval_config(eval_name: str) -> tuple[Any, Any]:
    # One dataset_column-sourced variable (the large mapped column) plus one
    # experiment_output-sourced variable, mirroring a real llm-judge eval.
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
    """The create path must flush + release each dataset row's ORM objects
    before building the next row, so peak in-session memory is bounded to a
    single row's test case + prompt results + eval scores rather than the whole
    N x P x E matrix. This guards against the create-time OOM regression."""
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

    # Track add / flush / expunge ordering so we can compute the live-object
    # peak and confirm flushing is interleaved per row (not a single flush at
    # the end).
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

    # Flush once per row (the regression this test guards would flush exactly
    # once, at the very end).
    assert db_session.flush.call_count == num_rows

    # Every created object is expunged (released from the identity map).
    assert db_session.add.call_count == num_rows * objects_per_row
    assert db_session.expunge.call_count == num_rows * objects_per_row

    # Replay the event stream to confirm peak live objects never exceeds a
    # single row's worth -- i.e. each row's objects are flushed and expunged
    # before the next row is built.
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
    """Summary aggregation must stream COMPLETED test cases page by page,
    expunging each page before loading the next, so peak in-session memory is
    bounded to a single page rather than the whole N x P x E matrix of
    duplicated eval_input_variables. This guards against the run-time read-back
    OOM regression (the executor previously loaded every test case -- and thus
    every per-cell context copy -- at once)."""
    batch_size = 2
    num_test_cases = 5
    test_cases = [SimpleNamespace(id=f"tc-{i}") for i in range(num_test_cases)]

    # A single ordered event stream of yields and expunges lets us replay the
    # live-object count and confirm each page is released before the next loads.
    events: list[tuple[str, str]] = []
    db_session = MagicMock()
    db_session.expunge.side_effect = lambda obj: events.append(("expunge", obj.id))

    repo = PromptExperimentRepository(db_session)

    # Serve pages via _get_db_test_cases, enforcing the streaming contract:
    # only COMPLETED test cases, eval_input_variables deferred, offset/limit
    # paging.
    pages_requested: list[tuple[Optional[int], Optional[int]]] = []

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

    repo._get_db_test_cases = fake_get_db_test_cases  # type: ignore[method-assign]

    yielded: list[str] = []
    for test_case in repo.iter_completed_test_cases_for_summary(
        "exp-1",
        batch_size=batch_size,
    ):
        yielded.append(test_case.id)
        events.append(("yield", test_case.id))

    # Every test case is yielded exactly once, in order (no drops, dupes, or
    # reordering that would change aggregation).
    assert yielded == [tc.id for tc in test_cases]

    # Every yielded test case is expunged exactly once.
    expunged = sorted(obj_id for kind, obj_id in events if kind == "expunge")
    assert expunged == sorted(tc.id for tc in test_cases)

    # Paging advances by batch_size and stops on the first empty page.
    assert pages_requested == [(0, 2), (2, 2), (4, 2), (6, 2)]

    # Replay the event stream: peak live (yielded-but-not-yet-expunged) objects
    # never exceeds one page. The regression this guards would hold all
    # num_test_cases at once (peak == num_test_cases).
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
