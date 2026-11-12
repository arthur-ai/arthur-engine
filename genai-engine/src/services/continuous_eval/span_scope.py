"""Span-scope continuous evals: which spans get a run, and how their verdicts decide
the trace.

A span-scope eval gives each sampled trace one rollup row (run_level 'span_rollup').
When the trace has been idle long enough, the rollup's job fans out: it picks the
spans matching the eval's span_filter, in tree order, up to max_spans_per_trace,
and creates one span run (run_level 'span') for each. Each span run calls the judge
once. When the last span run finishes, the rollup takes its status, score and label
from them by the eval's rollup_rule. The rollup itself never calls the judge.
"""

import os
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Sequence

from arthur_common.models.enums import ContinuousEvalRunStatus

from schemas.common_schemas import ContinuousEvalSpanFilter
from schemas.enums import (
    ContinuousEvalRollupRule,
    ContinuousEvalRunLevel,
    ContinuousEvalScope,
)
from utils.transform_executor import FilterableSpan, span_meets_condition


def _seconds_from_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, default)))
    except ValueError:
        return default


# A span-scope trace is fanned out once no span has arrived for this long, so the
# eval sees the spans that arrive late (tool calls, the final answer).
SPAN_SCOPE_IDLE_SECONDS = _seconds_from_env("GENAI_ENGINE_SPAN_SCOPE_IDLE_SECONDS", 60)
# ...but never later than this after the trace was first queued, so a trace that
# keeps growing is still judged.
SPAN_SCOPE_MAX_WAIT_SECONDS = _seconds_from_env(
    "GENAI_ENGINE_SPAN_SCOPE_MAX_WAIT_SECONDS",
    600,
)

# Where a span-scope eval checks its daily spend cap. "fan_out" (the default)
# checks once, before any span run of the trace is created: a trace is judged in
# full or not at all, and the last trace before the cap may overshoot it by up to
# max_spans_per_trace judge calls. "span_run" would also check before every span
# run, stopping exactly at the cap but leaving traces half judged.
# OPEN DECISION (Krishna): keep "fan_out", or switch to "span_run".
SPAN_SCOPE_CAP_CHECK_AT = os.environ.get(
    "GENAI_ENGINE_SPAN_SCOPE_CAP_CHECK_AT",
    "fan_out",
)


def first_run_level(scope: str) -> ContinuousEvalRunLevel:
    """The run a trace gets when queued: the trace run itself in trace scope, the
    rollup that fans out to span runs in span scope."""
    if scope == ContinuousEvalScope.SPAN.value:
        return ContinuousEvalRunLevel.SPAN_ROLLUP
    return ContinuousEvalRunLevel.TRACE


def cap_checked_before_each_span_run() -> bool:
    return SPAN_SCOPE_CAP_CHECK_AT == "span_run"


class SelectableSpan(FilterableSpan, Protocol):
    @property
    def span_id(self) -> str: ...

    @property
    def span_kind(self) -> Optional[str]: ...


def span_matches_filter(
    span: SelectableSpan,
    span_filter: ContinuousEvalSpanFilter,
) -> bool:
    """Name, kind and every condition, checked against this span alone."""
    if span_filter.span_name is not None and span.span_name != span_filter.span_name:
        return False
    if span_filter.span_kind is not None and span.span_kind != span_filter.span_kind:
        return False
    return all(span_meets_condition(span, c) for c in span_filter.conditions)


def select_spans(
    ordered_spans: Sequence[Any],
    span_filter: ContinuousEvalSpanFilter,
) -> list[Any]:
    """The spans to judge, in the given (tree) order."""
    return [span for span in ordered_spans if span_matches_filter(span, span_filter)]


@dataclass(frozen=True)
class SpanVerdict:
    """A finished or unfinished span run, as the rollup sees it."""

    span_id: str
    parent_span_id: Optional[str]
    span_name: Optional[str]
    status: ContinuousEvalRunStatus
    label: Optional[str] = None


@dataclass(frozen=True)
class RollupDecision:
    status: ContinuousEvalRunStatus
    score: Optional[int]
    label: Optional[str]
    description: str


_UNFINISHED = (ContinuousEvalRunStatus.PENDING, ContinuousEvalRunStatus.RUNNING)


def _deciding_runs(
    verdicts: Sequence[SpanVerdict],
    rule: ContinuousEvalRollupRule,
) -> list[SpanVerdict]:
    if rule == ContinuousEvalRollupRule.ANY_FAIL:
        return list(verdicts)
    # final_attempt: the last run (tree order) of each span name under one parent.
    last: dict[tuple[Optional[str], Optional[str]], SpanVerdict] = {}
    for verdict in verdicts:
        last[(verdict.parent_span_id, verdict.span_name)] = verdict
    return [v for v in verdicts if last[(v.parent_span_id, v.span_name)] is v]


def decide_rollup(
    verdicts: Sequence[SpanVerdict],
    rule: ContinuousEvalRollupRule,
    not_judged: int = 0,
) -> Optional[RollupDecision]:
    """The trace's verdict from its span runs (given in tree order), or None while
    any is still pending or running.

    The trace fails when a deciding span run failed; its label is that run's label
    (the first failing one in tree order). Otherwise an errored deciding run makes
    the rollup an error, all-skipped makes it skipped, and anything else passes.
    """
    if any(v.status in _UNFINISHED for v in verdicts):
        return None
    deciding = _deciding_runs(verdicts, rule)
    failed = [v for v in deciding if v.status == ContinuousEvalRunStatus.FAILED]
    errored = [v for v in deciding if v.status == ContinuousEvalRunStatus.ERROR]
    passed = [v for v in verdicts if v.status == ContinuousEvalRunStatus.PASSED]
    judged = [
        v
        for v in verdicts
        if v.status in (ContinuousEvalRunStatus.PASSED, ContinuousEvalRunStatus.FAILED)
    ]
    summary = f"{len(passed)} of {len(judged)} judged spans passed ({rule.value})"
    if not_judged:
        summary += f"; {not_judged} more matching spans past max_spans_per_trace"
    overruled = [
        v
        for v in verdicts
        if v.status == ContinuousEvalRunStatus.FAILED and v not in deciding
    ]
    if overruled:
        summary += "; later attempts overrule failed span " + ", ".join(
            v.span_id for v in overruled
        )

    if failed:
        first = failed[0]
        reason = f"span {first.span_id}" + (f" ({first.label})" if first.label else "")
        return RollupDecision(
            status=ContinuousEvalRunStatus.FAILED,
            score=0,
            label=first.label,
            description=f"Failed on {reason}. {summary}.",
        )
    if errored:
        return RollupDecision(
            status=ContinuousEvalRunStatus.ERROR,
            score=None,
            label=None,
            description=(
                "Span runs errored: "
                + ", ".join(v.span_id for v in errored)
                + f". {summary}."
            ),
        )
    if not judged:
        return RollupDecision(
            status=ContinuousEvalRunStatus.SKIPPED,
            score=None,
            label=None,
            description=f"Every span run was skipped. {summary}.",
        )
    return RollupDecision(
        status=ContinuousEvalRunStatus.PASSED,
        score=1,
        label=None,
        description=f"Passed. {summary}.",
    )
