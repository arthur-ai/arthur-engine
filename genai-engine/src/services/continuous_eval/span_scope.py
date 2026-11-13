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
from typing import Iterable, Optional, Sequence

from arthur_common.models.enums import ContinuousEvalRunStatus

from schemas.enums import (
    ContinuousEvalRollupRule,
    ContinuousEvalRunLevel,
    ContinuousEvalScope,
)
from schemas.transform_schemas import TraceTransformDefinition, TransformSpanSelector


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
# OPEN DECISION (maintainers): keep "fan_out", or switch to "span_run".
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


def judged_span_variables(
    definition: TraceTransformDefinition,
    mapped_variables: Iterable[str],
) -> list[str]:
    """The mapped transform variables that read the judged span (span_selector
    'current'). They are the only input that differs between a trace's span runs."""
    mapped = set(mapped_variables)
    return sorted(
        variable.variable_name
        for variable in definition.variables
        if variable.span_selector == TransformSpanSelector.CURRENT
        and variable.variable_name in mapped
    )


def scope_variables_problem(
    scope: str,
    definition: TraceTransformDefinition,
    mapped_variables: Iterable[str],
) -> Optional[str]:
    """Why the eval's mapped variables don't fit its scope, or None. A span-scope
    eval without a judged-span variable sends the judge the same input for every
    span; a trace-scope eval with one has no judged span and skips every trace."""
    reads_judged_span = judged_span_variables(definition, mapped_variables)
    if scope == ContinuousEvalScope.SPAN.value and not reads_judged_span:
        return (
            "A span-scope continuous eval must map a transform variable that reads "
            "the judged span (span_selector 'current'). Without one, every span run "
            "sends the judge the same input."
        )
    if scope == ContinuousEvalScope.TRACE.value and reads_judged_span:
        return (
            f"Transform variables {reads_judged_span} read the judged span "
            "(span_selector 'current'), which only exists in span scope. A "
            "trace-scope eval would skip every trace."
        )
    return None


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
    # A skipped run judged nothing, so it cannot overrule an earlier verdict: the
    # last run that was judged (or errored) decides, and a group that was skipped
    # throughout is decided by its last run.
    last: dict[tuple[Optional[str], Optional[str]], SpanVerdict] = {}
    for verdict in verdicts:
        key = (verdict.parent_span_id, verdict.span_name)
        if verdict.status != ContinuousEvalRunStatus.SKIPPED or (
            key not in last or last[key].status == ContinuousEvalRunStatus.SKIPPED
        ):
            last[key] = verdict
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
