"""The LLM insights of an onboarding analysis: one saved prompt per insight, over the sample.

Each insight is a prompt saved in the GenAI Engine's system task as
`onboarding_insight_<kind>`. Its user message takes one variable, `traces`: a batch of
sampled traces as text, each serialized with `tools.trace_serializer`, after a FACTS
block of per-trace hints that cheap rules extracted. The engine runs the prompt on its
default model and returns the model's JSON verdict and the call's cost:

    {"kind": ..., "fired": "yes" | "no" | "cannot_tell", "matched_traces": ["t01", ...],
     "example_span_name": ..., "reason": ...}

Traces go in batches that fit a fixed character budget, every insight is asked of every
batch, and the verdicts are merged per insight. Nothing here fails the job: a call that
still fails after its retries, a reply that is not a verdict, or the cost cap leaves that
insight's verdict out and says why, and the insights setting off skips them all.
"""

import json
import logging
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence

import requests

from tools.trace_serializer import MIN_MAX_CHARS, serialize_trace

# The GenAI Engine's system task, present on every engine, where the prompts are saved.
SYSTEM_TASK_ID = "fcba8383-55ce-42ec-a5c3-528f3492ea8a"
PROMPT_PREFIX = "onboarding_insight_"

INSIGHT_KINDS = (
    "internet_access",
    "tool_output_to_llm",
    "reference_material",
    "user_facing",
    "heavy_model",
    "tool_failures",
)

# The check each insight points to when it fires. A hint for the setup step, not a
# Platform id: the Platform builds the recommendation itself.
SUGGESTED_CHECK = {
    "internet_access": "a prompt-injection check on that tool's output",
    "tool_output_to_llm": "a prompt-injection check on the tool output that reaches the model",
    "reference_material": "a hallucination check that the answer is grounded in the material",
    "user_facing": "toxicity checks on model inputs and outputs, and a task-completion judge",
    "heavy_model": "a lighter model for this work (no check)",
    "tool_failures": "an error-recovery judge on the whole trace, and an alert on its failure rate",
}

# What one batch may hold, in characters: the prompts were tuned on batches of up to 89k
# tokens (a 200k context halved, less the prompt and the answer), at about 3 characters
# a token, with 15% margin for the estimate.
BATCH_CHAR_BUDGET = int(89_000 * 3 / 1.15)
TARGET_BATCH = 35
MAX_PARALLEL_CALLS = 5
COST_CAP_USD = 5.0
CALL_ATTEMPTS = 3
CALL_TIMEOUT_SECONDS = 300
FIRST_BACKOFF_SECONDS = 3.0


@dataclass(frozen=True)
class InsightSpan:
    """One span as the serializer reads it."""

    span_id: str
    parent_span_id: Optional[str]
    span_kind: Optional[str]
    span_name: Optional[str]
    status_code: Optional[str]
    start_time: datetime
    end_time: datetime
    raw_data: Any
    session_id: Optional[str] = None


@dataclass(frozen=True)
class PromptCompletion:
    content: str
    cost_usd: float


class InsightEngineClient(Protocol):
    def insights_enabled(self) -> bool: ...

    def run_prompt(self, prompt_name: str, traces_text: str) -> PromptCompletion: ...


class HttpInsightEngineClient:
    """The GenAI Engine's configuration and saved-prompt completions routes.

    Called over plain HTTP: the insights setting is newer than the generated client.
    """

    def __init__(self, host: str, api_key: str) -> None:
        self.host = host.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def insights_enabled(self) -> bool:
        resp = requests.get(
            f"{self.host}/api/v2/configuration",
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        # An engine that predates the setting has no insights prompts either.
        return bool(resp.json().get("insights_generation_enabled", False))

    def run_prompt(self, prompt_name: str, traces_text: str) -> PromptCompletion:
        resp = requests.post(
            f"{self.host}/api/v1/tasks/{SYSTEM_TASK_ID}/prompts/{prompt_name}"
            "/versions/latest/completions",
            headers=self.headers,
            json={
                "variables": [{"name": "traces", "value": traces_text}],
                "stream": False,
            },
            timeout=CALL_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        body = resp.json()
        return PromptCompletion(
            content=body.get("content") or "",
            cost_usd=float(body.get("cost") or 0),
        )


@dataclass
class MergedVerdict:
    """One insight's answer over every batch it was asked of."""

    kind: str
    fired: str  # yes, no or cannot_tell
    matched_trace_ids: list[str]
    example_span_name: Optional[str]
    reasons: list[str]
    suggested_check: Optional[str]


@dataclass
class InsightRun:
    insights_off: bool = False
    verdicts: list[MergedVerdict] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (kind, reason)
    cost_usd: float = 0.0
    calls: int = 0
    traces: int = 0


# ---------------------------------------------------------------- rule facts (no LLM)

_URL = re.compile(r"https?://[^\s\"']+|\b[a-z0-9-]+\.(?:com|org|net|io|ai|dev)\b", re.I)
_ERROR_IN_OUTPUT = re.compile(r'"?error"?\s*[:=]', re.I)


def _get(data: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str) if value else ""


def _attrs(span: InsightSpan) -> Any:
    return (
        (span.raw_data or {}).get("attributes") or {}
        if isinstance(span.raw_data, dict)
        else {}
    )


def _letters_and_digits(text: str) -> str:
    # Tool output usually reaches the next model call re-encoded (JSON inside a message,
    # escaped quotes), so it is compared on letters and digits only.
    return re.sub(r"[^a-z0-9]", "", text.lower())


def trace_facts(spans: Sequence[InsightSpan]) -> dict[str, Any]:
    """Per-trace hints the prompts read before the traces: evidence, not the answer."""
    tools = [s for s in spans if (s.span_kind or "").upper() == "TOOL"]
    llms = [s for s in spans if (s.span_kind or "").upper() == "LLM"]
    fed = set()
    for tool in tools:
        out = _letters_and_digits(_text(_get(_attrs(tool), "output.value")))
        if len(out) < 16:
            continue
        for llm in llms:
            seen = _letters_and_digits(_text(_get(_attrs(llm), "llm.input_messages")))
            if llm.start_time >= tool.end_time and out[:160] in seen:
                fed.add(f"{tool.span_name}->{llm.span_name}")
    return {
        "tools": sorted({t.span_name for t in tools if t.span_name}),
        "tool_input_urls": sorted(
            {
                t.span_name
                for t in tools
                if t.span_name and _URL.search(_text(_get(_attrs(t), "input.value")))
            },
        ),
        "tool_output_into_llm": sorted(fed),
        "retriever_spans": sum(
            (s.span_kind or "").upper() == "RETRIEVER" for s in spans
        ),
        "session": next((s.session_id for s in spans if s.session_id), None),
        "user": next(
            (u for s in spans if (u := _get(_attrs(s), "user.id"))),
            None,
        ),
        "models": sorted(
            {m for s in llms if (m := _get(_attrs(s), "llm.model_name"))},
        ),
        "tokens": sum(int(_get(_attrs(s), "llm.token_count.total") or 0) for s in llms),
        "guardrail_spans": sum(
            (s.span_kind or "").upper() == "GUARDRAIL" for s in spans
        ),
        "tool_errors": sorted(
            t.span_name or ""
            for t in tools
            if t.status_code == "Error"
            or _ERROR_IN_OUTPUT.search(_text(_get(_attrs(t), "output.value")))
        ),
    }


def _facts_line(short_id: str, facts: dict[str, Any]) -> str:
    parts = [
        f"{k}={','.join(map(str, v)) if isinstance(v, list) else v}"
        for k, v in facts.items()
        if v not in ([], None, 0)
    ]
    return f"{short_id}: " + "; ".join(parts)


# ---------------------------------------------------------------- batches


@dataclass(frozen=True)
class Batch:
    short_ids: list[str]
    text: str


def _render_batch(
    short_ids: list[str],
    traces: Mapping[str, Sequence[InsightSpan]],
    facts: dict[str, dict[str, Any]],
    max_chars: int,
) -> str:
    facts_block = "\n".join(_facts_line(t, facts[t]) for t in short_ids)
    traces_block = "\n\n".join(
        f"<trace id={t}>\n{serialize_trace(traces[t], max_chars=max_chars)[0]}\n</trace>"
        for t in short_ids
    )
    return f"FACTS\n{facts_block}\n\nTRACES\n{traces_block}"


def make_batches(
    traces: Mapping[str, Sequence[InsightSpan]],
    char_budget: int = BATCH_CHAR_BUDGET,
) -> tuple[list[Batch], list[str]]:
    """Batches within the budget, and the traces too large to send even alone."""
    facts = {t: trace_facts(spans) for t, spans in traces.items()}
    ids = list(traces)
    batches: list[Batch] = []
    too_large: list[str] = []
    i = 0
    while i < len(ids):
        size = min(TARGET_BATCH, len(ids) - i)
        while True:
            chunk = ids[i : i + size]
            max_chars = max(MIN_MAX_CHARS, char_budget // size)
            text = _render_batch(chunk, traces, facts, max_chars)
            if len(text) <= char_budget:
                batches.append(Batch(short_ids=chunk, text=text))
                i += size
                break
            if size == 1:
                too_large.append(chunk[0])
                i += 1
                break
            size = max(1, size // 2)
    return batches, too_large


# ---------------------------------------------------------------- calls


class _Spend:
    def __init__(self, cap_usd: float) -> None:
        self.cap_usd = cap_usd
        self.usd = 0.0
        self.calls = 0
        self.lock = threading.Lock()

    def over_cap(self) -> bool:
        with self.lock:
            return self.usd >= self.cap_usd

    def add(self, cost_usd: float) -> None:
        with self.lock:
            self.usd += cost_usd
            self.calls += 1


_JSON_OBJECT = re.compile(r"\{.*\}", re.S)


def _parse_verdict(content: str) -> Optional[dict[str, Any]]:
    match = _JSON_OBJECT.search(content)
    if not match:
        return None
    try:
        verdict = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(verdict, dict) or verdict.get("fired") not in (
        "yes",
        "no",
        "cannot_tell",
    ):
        return None
    return verdict


class _Asker:
    def __init__(
        self,
        client: InsightEngineClient,
        spend: _Spend,
        logger: logging.Logger,
        sleep: Callable[[float], None],
    ) -> None:
        self.client = client
        self.spend = spend
        self.logger = logger
        self.sleep = sleep

    def ask(self, batch: Batch, kind: str) -> dict[str, Any]:
        """The verdict, or {"skipped": reason}: never raises."""
        if self.spend.over_cap():
            return {"skipped": "cost_cap"}
        for attempt in range(CALL_ATTEMPTS):
            try:
                completion = self.client.run_prompt(PROMPT_PREFIX + kind, batch.text)
                break
            except Exception as e:
                if attempt == CALL_ATTEMPTS - 1:
                    # The type only: a provider's message can echo the prompt.
                    self.logger.warning(
                        f"Onboarding insight {kind} failed after {CALL_ATTEMPTS} attempts "
                        f"({type(e).__name__})",
                    )
                    return {"skipped": "model_unavailable"}
                self.sleep(FIRST_BACKOFF_SECONDS * 2**attempt)
        self.spend.add(completion.cost_usd)
        verdict = _parse_verdict(completion.content)
        return verdict if verdict is not None else {"skipped": "unparsed_reply"}


def _merge(
    kind: str,
    answers: list[dict[str, Any]],
    trace_ids: dict[str, str],
) -> tuple[Optional[MergedVerdict], Optional[str]]:
    """The insight's verdict over every batch, or why there is none."""
    verdicts = [a for a in answers if "skipped" not in a]
    if not verdicts:
        reasons = sorted({a["skipped"] for a in answers})
        return None, reasons[0] if reasons else "no_batches"
    fired = [v for v in verdicts if v["fired"] == "yes"]
    states = {v["fired"] for v in verdicts}
    if fired:
        state = "yes"
    elif "cannot_tell" in states or len(verdicts) < len(answers):
        # A batch that was not answered could have held the trace that shows it.
        state = "cannot_tell"
    else:
        state = "no"
    matched = {
        trace_ids[t]
        for v in fired
        for t in v.get("matched_traces") or []
        if isinstance(t, str) and t in trace_ids
    }
    return (
        MergedVerdict(
            kind=kind,
            fired=state,
            matched_trace_ids=sorted(matched),
            example_span_name=next(
                (
                    str(v["example_span_name"])
                    for v in fired
                    if v.get("example_span_name")
                ),
                None,
            ),
            reasons=[str(v.get("reason") or "") for v in verdicts if v.get("reason")],
            suggested_check=SUGGESTED_CHECK.get(kind) if state == "yes" else None,
        ),
        None,
    )


def run_llm_insights(
    client: InsightEngineClient,
    traces: Mapping[str, Sequence[InsightSpan]],
    logger: logging.Logger,
    cost_cap_usd: float = COST_CAP_USD,
    sleep: Callable[[float], None] = time.sleep,
) -> InsightRun:
    """Ask every insight of the sampled traces, keyed by trace id. Never raises."""
    run = InsightRun(traces=len(traces))
    try:
        enabled = client.insights_enabled()
    except Exception as e:
        logger.warning(f"Could not read the insights setting ({type(e).__name__})")
        run.skipped.append(("llm_insights", "model_unavailable"))
        return run
    if not enabled:
        run.insights_off = True
        run.skipped.append(("llm_insights", "insights_off"))
        return run

    # Short ids keep the prompt small, and are what the model cites back.
    short = {trace_id: f"t{i:02d}" for i, trace_id in enumerate(traces, 1)}
    trace_ids = {s: trace_id for trace_id, s in short.items()}
    batches, too_large = make_batches({short[t]: spans for t, spans in traces.items()})
    if too_large:
        logger.warning(
            f"{len(too_large)} sampled trace(s) too large to send for insights",
        )

    spend = _Spend(cost_cap_usd)
    asker = _Asker(client, spend, logger, sleep)
    answers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
        for batch in batches:
            # The first call alone, so the engine can cache the batch for the others.
            first, *rest = INSIGHT_KINDS
            answers[first].append(asker.ask(batch, first))
            for kind, answer in zip(
                rest,
                pool.map(lambda k: asker.ask(batch, k), rest),
            ):
                answers[kind].append(answer)

    for kind in INSIGHT_KINDS:
        verdict, reason = _merge(kind, answers[kind], trace_ids)
        if verdict is not None:
            run.verdicts.append(verdict)
        else:
            run.skipped.append((kind, reason or "no_batches"))
    run.cost_usd = spend.usd
    run.calls = spend.calls
    logger.info(
        f"Onboarding insights: {run.calls} calls over {len(batches)} batch(es) of "
        f"{len(traces)} traces in {time.monotonic() - started:.0f}s, "
        f"cost ${run.cost_usd:.2f} (cap ${cost_cap_usd:.2f})",
    )
    return run
