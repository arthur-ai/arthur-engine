"""The ML engine's copy of the GenAI Engine's trace serializer: what it cuts, and that the
two copies stay in step."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pytest

from tools.trace_serializer import serialize_trace

REPO_ROOT = Path(__file__).resolve().parents[4]
ML_TOOLS = REPO_ROOT / "ml-engine" / "src" / "ml_engine" / "tools"
GENAI_UTILS = REPO_ROOT / "genai-engine" / "src" / "utils"

T0 = datetime(2026, 11, 1)


@dataclass(frozen=True)
class Span:
    span_id: str
    parent_span_id: Optional[str]
    span_kind: Optional[str]
    span_name: Optional[str]
    status_code: Optional[str]
    start_time: datetime
    end_time: datetime
    raw_data: Any


def _span(span_id: str, parent: Optional[str], kind: str, io: tuple[str, str]) -> Span:
    return Span(
        span_id=span_id,
        parent_span_id=parent,
        span_kind=kind,
        span_name=f"{kind.lower()}-{span_id}",
        status_code="Ok",
        start_time=T0 + timedelta(seconds=len(span_id)),
        end_time=T0 + timedelta(seconds=10),
        raw_data={
            "attributes": {"input": {"value": io[0]}, "output": {"value": io[1]}},
        },
    )


def _trace(tool_result: str, model_output: str) -> list[Span]:
    return [
        _span("a", None, "AGENT", ("question", "answer")),
        _span("ab", "a", "TOOL", ('{"id": 1}', tool_result)),
        _span("abc", "a", "LLM", ("prompt", model_output)),
    ]


def test_a_trace_that_fits_its_budget_is_not_cut() -> None:
    text, stats = serialize_trace(_trace("R" * 3_000, "L" * 3_000), max_chars=48_000)

    assert stats.truncated is False
    assert stats.fields_shortened == 0
    assert text.count("R") >= 3_000 and text.count("L") >= 3_000
    assert "TRUNCATED" not in text


def test_a_trace_over_its_budget_is_cut_and_says_so() -> None:
    spans = _trace("R" * 3_000, "L" * 3_000)
    _, whole = serialize_trace(spans, max_chars=48_000)

    text, stats = serialize_trace(spans, max_chars=whole.full_chars - 300)

    assert stats.truncated is True
    assert stats.fields_shortened == 2  # both long fields take the first cap, 2,000
    assert text.count("R") < 2_100 and text.count("L") < 2_100
    assert "[TRUNCATED view of 3 spans" in text
    assert "2 fields shortened" in text


def _normalized(source: str) -> str:
    """The module without its leading provenance comment, with the GenAI Engine's import
    path, so the two copies compare equal when they are in step."""
    source = re.sub(r"\A(#[^\n]*\n)+\n", "", source)
    return source.replace("from tools.span_tree", "from utils.span_tree").replace(
        "(tools.span_tree,",
        "(utils.span_tree,",
    )


@pytest.mark.parametrize("module", ["trace_serializer.py", "span_tree.py"])
def test_the_copy_matches_the_genai_engine_module(module: str) -> None:
    original = GENAI_UTILS / module
    if not original.exists():
        pytest.skip(f"genai-engine/src/utils/{module} is not in this checkout yet")

    assert _normalized((ML_TOOLS / module).read_text()) == _normalized(
        original.read_text(),
    ), (
        f"ml-engine's copy of {module} differs from the GenAI Engine's: "
        "change both, then update the commit named at the top of the copy"
    )
