"""The LLM insights of an onboarding analysis: one saved prompt per insight, over the sample.

Each insight is a prompt saved in the GenAI Engine's system task as
`onboarding_insight_<kind>`; the version tagged `production` runs. Its user message takes
one variable, `traces`: a batch of sampled traces as text, each serialized with
`tools.trace_serializer`, after a FACTS block of per-trace hints that cheap rules
extracted. The engine runs the prompt on its default model provider, which must support
structured output, and returns the model's verdict, in the prompt's JSON schema, and the
call's cost:

    {"kind": ..., "fired": "yes" | "no" | "cannot_tell", "matched_traces": ["t01", ...],
     "example_span_name": ... or "", "reason": ...}

Traces go in batches that fit a fixed character budget, every insight is asked of every
batch, and the verdicts are merged per insight. Nothing here fails the job: a call that
still fails after its retries, a reply that is not a verdict, or the cost cap leaves that
insight's verdict out and says why. No default model provider on the engine, which is
how insights are turned off, or the engine refusing a call (the default model cannot give
structured output) skips them all.
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

import litellm
import requests

from tools.trace_serializer import MIN_MAX_CHARS, serialize_trace

# The GenAI Engine's system task, present on every engine, where the prompts are saved.
SYSTEM_TASK_ID = "fcba8383-55ce-42ec-a5c3-528f3492ea8a"
PROMPT_PREFIX = "onboarding_insight_"
# Groups one analysis's prompt runs in the engine's system task (one session, one trace).
SESSION_HEADER = "X-Arthur-Session-Id"

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

# What one batch may hold. The prompts were tuned on batches of up to 89k tokens: a 200k
# input window halved, less the prompt and the answer. A model with a smaller input window
# gets half of it, less the same reserve; a larger one keeps the tuned size.
MAX_BATCH_TOKENS = 89_000
PROMPT_AND_ANSWER_TOKENS = 11_000


def _chars(tokens: int) -> int:
    """About 3 characters a token, with 15% margin for the estimate."""
    return int(tokens * 3 / 1.15)


BATCH_CHAR_BUDGET = _chars(MAX_BATCH_TOKENS)
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


@dataclass(frozen=True)
class DefaultModel:
    """The GenAI Engine's default model provider, which runs the insight prompts."""

    provider: str
    model_name: str


def batch_char_budget(model: DefaultModel) -> int:
    """The batch budget for the model's input window. litellm's model map (the one the
    GenAI Engine uses, through the same pinned arthur-common) gives max_input_tokens; its
    max_tokens is the output limit and says nothing about the input. A model litellm does
    not know (an Azure deployment name) keeps the tuned size."""
    try:
        window = litellm.get_model_info(
            model=model.model_name,
            custom_llm_provider=model.provider,
        ).get("max_input_tokens")
    except Exception:
        window = None
    if not window:
        return BATCH_CHAR_BUDGET
    tokens = min(MAX_BATCH_TOKENS, window // 2 - PROMPT_AND_ANSWER_TOKENS)
    return max(0, _chars(tokens))


class PromptTooLarge(Exception):
    """The batch is longer than the model's input window (HTTP 413). Only this call is
    affected: a smaller batch could still fit."""


class PromptRejected(Exception):
    """The engine refused the call (a 4xx other than a timeout or rate limit): the same
    call would be refused again, as would the other prompts on the same model."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


# Client errors that a retry can get past.
_RETRYABLE_CLIENT_ERRORS = {408, 429}
_CONTENT_TOO_LARGE = 413


class InsightEngineClient(Protocol):
    def default_model(self) -> Optional[DefaultModel]: ...

    def run_prompt(self, prompt_name: str, traces_text: str) -> PromptCompletion: ...


class HttpInsightEngineClient:
    """The GenAI Engine's default model provider and saved-prompt completions routes.

    Called over plain HTTP: both are newer than the generated client.
    Every call carries `session_id` as X-Arthur-Session-Id: the engine records each run
    of a system task prompt as an LLM span there, and runs with one session id share a
    session and a trace, so one analysis's calls read as one trace.
    """

    def __init__(
        self,
        host: str,
        api_key: str,
        session_id: Optional[str] = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.session_id = session_id
        if session_id:
            self.headers[SESSION_HEADER] = session_id

    def report_session(self, summary: dict[str, Any]) -> None:
        """Tell the engine what the whole analysis did, so its trace in the system task
        covers the job from start to end, like the chatbot's does a turn. Counts and
        verdicts only, never trace content."""
        if not self.session_id:
            return
        resp = requests.put(
            f"{self.host}/api/v1/tasks/{SYSTEM_TASK_ID}/prompt_sessions/"
            f"{self.session_id}/summary",
            headers=self.headers,
            json=summary,
            timeout=30,
        )
        resp.raise_for_status()

    def default_model(self) -> Optional[DefaultModel]:
        resp = requests.get(
            f"{self.host}/api/v1/default_model_provider",
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("provider") or not body.get("model_name"):
            return None
        return DefaultModel(provider=body["provider"], model_name=body["model_name"])

    def run_prompt(self, prompt_name: str, traces_text: str) -> PromptCompletion:
        resp = requests.post(
            f"{self.host}/api/v1/tasks/{SYSTEM_TASK_ID}/prompts/{prompt_name}"
            "/versions/production/completions",
            headers=self.headers,
            json={
                "variables": [{"name": "traces", "value": traces_text}],
                "stream": False,
            },
            timeout=CALL_TIMEOUT_SECONDS,
        )
        if resp.status_code == _CONTENT_TOO_LARGE:
            raise PromptTooLarge()
        if 400 <= resp.status_code < 500 and (
            resp.status_code not in _RETRYABLE_CLIENT_ERRORS
        ):
            raise PromptRejected(resp.status_code)
        resp.raise_for_status()
        body = resp.json()
        content = body.get("content")
        if isinstance(content, dict):
            # A verdict returned as an object rather than as JSON text.
            content = json.dumps(content)
        return PromptCompletion(
            content=content if isinstance(content, str) else "",
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
    # Traces in the batches that answered this insight: what its verdict covers.
    traces_answered: int = 0


@dataclass
class InsightRun:
    verdicts: list[MergedVerdict] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (kind, reason)
    cost_usd: float = 0.0
    calls: int = 0
    traces: int = 0  # traces in the batches at least one insight was answered for
    sampled: int = 0  # traces in the sample handed to the run


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


def _count(value: Any) -> int:
    """A count from span attributes, or 0 when it is not a number."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


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
        "tokens": sum(_count(_get(_attrs(s), "llm.token_count.total")) for s in llms),
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


def _trace_block(short_id: str, text: str) -> str:
    return f"<trace id={short_id}>\n{text}\n</trace>"


def _render_batch(
    short_ids: list[str],
    traces: Mapping[str, Sequence[InsightSpan]],
    facts: dict[str, dict[str, Any]],
    char_budget: int,
) -> str:
    """The batch's text. Each trace gets an equal share of what the facts and the
    framing leave of the budget, so a trace that fits its share is sent whole."""
    facts_block = "\n".join(_facts_line(t, facts[t]) for t in short_ids)
    head = f"FACTS\n{facts_block}\n\nTRACES\n"
    framing = len(head) + sum(len(_trace_block(t, "")) + 2 for t in short_ids)
    max_chars = max(MIN_MAX_CHARS, (char_budget - framing) // len(short_ids))
    traces_block = "\n\n".join(
        _trace_block(t, serialize_trace(traces[t], max_chars=max_chars)[0])
        for t in short_ids
    )
    return head + traces_block


def _readable(
    traces: Mapping[str, Sequence[InsightSpan]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """The facts of each trace that can be read, and the traces that cannot: span data
    the serializer cannot handle leaves that trace out, not the run."""
    facts: dict[str, dict[str, Any]] = {}
    unreadable: list[str] = []
    for short_id, spans in traces.items():
        try:
            trace = trace_facts(spans)
            serialize_trace(spans, max_chars=MIN_MAX_CHARS)
        except Exception:
            unreadable.append(short_id)
        else:
            facts[short_id] = trace
    return facts, unreadable


def make_batches(
    traces: Mapping[str, Sequence[InsightSpan]],
    char_budget: int = BATCH_CHAR_BUDGET,
) -> tuple[list[Batch], list[str], list[str]]:
    """Batches within the budget, the traces too large to send even alone, and the
    traces that could not be read."""
    facts, unreadable = _readable(traces)
    ids = [t for t in traces if t in facts]
    batches: list[Batch] = []
    too_large: list[str] = []
    i = 0
    while i < len(ids):
        size = min(TARGET_BATCH, len(ids) - i)
        while True:
            chunk = ids[i : i + size]
            text = _render_batch(chunk, traces, facts, char_budget)
            if len(text) <= char_budget:
                batches.append(Batch(short_ids=chunk, text=text))
                i += size
                break
            if size == 1:
                too_large.append(chunk[0])
                i += 1
                break
            size = max(1, size // 2)
    return batches, too_large, unreadable


# ---------------------------------------------------------------- calls


class _Spend:
    """The run's spend against its cap. Each call reserves its estimated cost before it
    is sent, so calls running in parallel cannot together pass the cap: a call is sent
    only while the spend so far plus every reservation, its own included, stays within
    it. The estimate is the highest cost per character of batch seen so far, times this
    batch's length; before any call has finished it is 0, and the first call of the
    first batch runs alone."""

    def __init__(self, cap_usd: float) -> None:
        self.cap_usd = cap_usd
        self.usd = 0.0
        self.reserved = 0.0
        self.calls = 0
        self.usd_per_char = 0.0
        self.lock = threading.Lock()

    def reserve(self, chars: int) -> Optional[float]:
        """The amount reserved for a call on `chars` characters, or None when it would
        pass the cap."""
        with self.lock:
            estimate = self.usd_per_char * chars
            if self.usd >= self.cap_usd or (
                self.usd + self.reserved + estimate > self.cap_usd
            ):
                return None
            self.reserved += estimate
            return estimate

    def release(self, reserved: float) -> None:
        with self.lock:
            self.reserved -= reserved

    def settle(self, reserved: float, cost_usd: float, chars: int) -> None:
        with self.lock:
            self.reserved -= reserved
            self.usd += cost_usd
            self.calls += 1
            if chars:
                self.usd_per_char = max(self.usd_per_char, cost_usd / chars)


_JSON_OBJECT = re.compile(r"\{.*\}", re.S)
VERDICT_FIELDS = ("kind", "fired", "matched_traces", "example_span_name", "reason")


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
    matched = verdict.get("matched_traces", [])
    if not isinstance(matched, list) or not all(isinstance(t, str) for t in matched):
        return None
    # Only the verdict's own fields: a key the model adds (such as `skipped`, which marks
    # an unanswered call here) must not reach the merge.
    return {k: verdict[k] for k in VERDICT_FIELDS if k in verdict}


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
        # Set by the first refused call; no later call is made.
        self.rejected = threading.Event()

    def ask(self, batch: Batch, kind: str) -> dict[str, Any]:
        """The verdict, or {"skipped": reason}: never raises."""
        for attempt in range(CALL_ATTEMPTS):
            # Before every attempt: another call may have been refused, or reached the
            # cap, while this one waited out its backoff.
            if self.rejected.is_set():
                return {"skipped": "model_rejected"}
            reserved = self.spend.reserve(len(batch.text))
            if reserved is None:
                return {"skipped": "cost_cap"}
            try:
                completion = self.client.run_prompt(PROMPT_PREFIX + kind, batch.text)
            except PromptTooLarge:
                self.spend.release(reserved)
                self.logger.warning(
                    f"Onboarding insight {kind}: a batch of {len(batch.short_ids)} "
                    "traces is longer than the default model's input window",
                )
                return {"skipped": "too_large"}
            except PromptRejected as e:
                self.spend.release(reserved)
                # The engine's message is not logged: it can name the prompt's text.
                self.logger.warning(
                    f"Onboarding insight {kind} refused by the engine ({e}); "
                    "skipping the remaining insight calls",
                )
                self.rejected.set()
                return {"skipped": "model_rejected"}
            except Exception as e:
                self.spend.release(reserved)
                if attempt == CALL_ATTEMPTS - 1:
                    # The type only: a provider's message can echo the prompt.
                    self.logger.warning(
                        f"Onboarding insight {kind} failed after {CALL_ATTEMPTS} attempts "
                        f"({type(e).__name__})",
                    )
                    return {"skipped": "model_unavailable"}
                self.sleep(FIRST_BACKOFF_SECONDS * 2**attempt)
            else:
                self.spend.settle(reserved, completion.cost_usd, len(batch.text))
                break
        verdict = _parse_verdict(completion.content)
        if verdict is None:
            return {"skipped": "unparsed_reply"}
        # Only traces this batch held: the model cannot have seen any other.
        shown = set(batch.short_ids)
        verdict["matched_traces"] = [
            t for t in verdict.get("matched_traces", []) if t in shown
        ]
        return verdict


def _merge(
    kind: str,
    asked: list[tuple[dict[str, Any], int]],
    trace_ids: dict[str, str],
) -> tuple[Optional[MergedVerdict], Optional[str]]:
    """The insight's verdict over every batch, or why there is none. `asked` holds each
    batch's answer with the number of traces that batch held."""
    answers = [answer for answer, _ in asked]
    verdicts = [a for a in answers if "skipped" not in a]
    if not verdicts:
        reasons = sorted({a["skipped"] for a in answers})
        return None, reasons[0] if reasons else None
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
            traces_answered=sum(n for answer, n in asked if "skipped" not in answer),
        ),
        None,
    )


def run_llm_insights(
    client: InsightEngineClient,
    traces: Mapping[str, Sequence[InsightSpan]],
    logger: logging.Logger,
    cost_cap_usd: float = COST_CAP_USD,
    sleep: Optional[Callable[[float], None]] = None,
) -> InsightRun:
    """Ask every insight of the sampled traces, keyed by trace id. Never raises.

    `sleep` waits out a retry's backoff; by default `time.sleep`, looked up when the
    run starts so that a test can patch it."""
    sleep = sleep or time.sleep
    run = InsightRun(traces=len(traces))
    # The prompts name no model, so the default model provider is what turns insights
    # on: with none set they are off, and no call is made.
    try:
        default_model = client.default_model()
    except Exception as e:
        logger.warning(
            f"Could not read the default model provider ({type(e).__name__})"
        )
        run.skipped.append(("llm_insights", "model_unavailable"))
        return run
    if default_model is None:
        run.skipped.append(("llm_insights", "default_model_not_configured"))
        return run

    # Short ids keep the prompt small, and are what the model cites back.
    short = {trace_id: f"t{i:02d}" for i, trace_id in enumerate(traces, 1)}
    trace_ids = {s: trace_id for trace_id, s in short.items()}
    batches, too_large, unreadable = make_batches(
        {short[t]: spans for t, spans in traces.items()},
        char_budget=batch_char_budget(default_model),
    )
    if too_large:
        logger.warning(
            f"{len(too_large)} sampled trace(s) too large to send for insights",
        )
    if unreadable:
        logger.warning(
            f"{len(unreadable)} sampled trace(s) could not be read for insights",
        )
    run.sampled = len(traces)

    spend = _Spend(cost_cap_usd)
    asker = _Asker(client, spend, logger, sleep)
    answers: dict[str, list[tuple[dict[str, Any], int]]] = defaultdict(list)
    analysed = 0
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
        for batch in batches:
            # The first call alone, so a provider that caches a repeated prompt prefix
            # by itself (OpenAI does) can serve the batch to the other five from its
            # cache. The engine marks no saved prompt for caching, so Anthropic does not.
            first, *rest = INSIGHT_KINDS
            batch_answers = [(first, asker.ask(batch, first))]
            batch_answers += zip(rest, pool.map(lambda k: asker.ask(batch, k), rest))
            for kind, answer in batch_answers:
                answers[kind].append((answer, len(batch.short_ids)))
            if any("skipped" not in answer for _, answer in batch_answers):
                analysed += len(batch.short_ids)
    # The traces the findings speak for: those in a batch the model answered for.
    run.traces = analysed

    for kind in INSIGHT_KINDS:
        verdict, reason = _merge(kind, answers[kind], trace_ids)
        if verdict is not None:
            run.verdicts.append(verdict)
        else:
            # With nothing sent, say why no trace could be.
            if reason is None:
                reason = (
                    "too_large"
                    if too_large
                    else "unreadable" if unreadable else "no_batches"
                )
            run.skipped.append((kind, reason))
    if any(
        a.get("skipped") == "cost_cap" for kind in answers for a, _ in answers[kind]
    ):
        # The findings then cover only the traces analysed before the cap.
        run.skipped.append(("llm_insights", "cost_cap_reached"))
        logger.warning(
            f"Onboarding insights stopped at the ${cost_cap_usd:.2f} cost cap: "
            f"{run.traces} of {run.sampled} sampled traces analysed",
        )
    run.cost_usd = spend.usd
    run.calls = spend.calls
    logger.info(
        f"Onboarding insights: {run.calls} calls over {len(batches)} batch(es), "
        f"{run.traces} of {len(traces)} traces analysed, in "
        f"{time.monotonic() - started:.0f}s, "
        f"cost ${run.cost_usd:.2f} (cap ${cost_cap_usd:.2f})",
    )
    return run
