#!/usr/bin/env python3
"""
claude_code_circuit_breaker.py — burn-rate circuit breaker for Claude Code.

Reads the LLM spend that claude_code_tracer.py ships to Arthur Engine and trips
when the spend *burn rate* exceeds the configured budget. While tripped it
blocks new prompts and halts the in-flight turn, so a runaway agent loop stops
costing money until the breaker cools down or is reset by hand.

Burn rate follows the SRE error-budget definition:

    burn_rate = (spend in window / window hours) / (budget_usd / budget_period_hours)

A burn rate of 1.0 means the budget would be used up exactly at the end of the
period. Each rule pairs a long window with a short one (multi-window alerting):
the long window says the burn is significant, the short window says it is still
happening. A rule fires only when both exceed its burn_rate threshold.

Hook events:
  user_prompt_submit — block the prompt while the breaker is open
  pre_tool           — deny the tool call and stop the turn while the breaker is open
  session_start      — tell the user if the breaker is already open

CLI:
  status [--session ID]  — print the current spend/burn-rate evaluation as JSON
  reset                  — close the breaker (clears persisted state)

Engine credentials come from the same place the tracer reads them (env vars,
then <project>/.claude/arthur_config.json, then ~/.claude/arthur_config.json).
Breaker settings come from ARTHUR_BREAKER_CONFIG, then
<project>/.claude/arthur_circuit_breaker.json, then
~/.claude/arthur_circuit_breaker.json, falling back to DEFAULT_CONFIG. With no
engine credentials configured the hook is a silent no-op, like the tracer.
"""

import contextlib
import fcntl
import hashlib
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Logging — stderr only so stdout stays clean for Claude hooks
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="[claude_code_circuit_breaker] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("claude_code_circuit_breaker")


# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    # Set false to install the hooks but leave them inert.
    "enabled": True,
    # Whose spend to measure: "session" (this Claude Code session), "user"
    # (every session of this OS user on the task) or "task" (every session).
    "scope": "session",
    # The spend budget and the period it is meant to last.
    "budget_usd": 100.0,
    "budget_period_hours": 24.0,
    # Multi-window burn-rate rules. A rule fires when spend over both
    # window_minutes and short_window_minutes exceeds burn_rate times the
    # budget rate. short_window_minutes may be null for a single window.
    "rules": [
        {
            "name": "fast-burn",
            "window_minutes": 10,
            "short_window_minutes": 2,
            "burn_rate": 14.4,
        },
        {
            "name": "slow-burn",
            "window_minutes": 60,
            "short_window_minutes": 10,
            "burn_rate": 6.0,
        },
    ],
    # Absolute spend ceiling for the scope (whole session, or the budget
    # period for user/task scope). null disables it.
    "hard_cap_usd": None,
    # Emit a warning once a rule reaches this fraction of its threshold.
    "warn_fraction": 0.75,
    # PreToolUse fires on every tool call; between checks the last verdict
    # is reused so the engine is queried at most once per interval.
    "check_interval_seconds": 30,
    # How long the breaker stays open before it probes the engine again.
    "cooldown_minutes": 15,
    # What to do when the engine cannot be reached: "open" keeps working,
    # "closed" trips the breaker.
    "fail_mode": "open",
    "http_timeout_seconds": 5,
    # Spans whose model Arthur Engine could not price carry no cost. These
    # per-million-token rates fill the gap so the breaker is not blind to
    # them; null leaves such spans at $0 and warns instead.
    "fallback_usd_per_million_tokens": None,
}

CONFIG_ENV = "ARTHUR_BREAKER_CONFIG"
BYPASS_ENV = "ARTHUR_BREAKER_BYPASS"
STATE_DIR = Path.home() / ".claude" / "circuit_breaker"
STATE_MAX_AGE_S = 48 * 3600
SPAN_PAGE_SIZE = 5000
SPAN_MAX_PAGES = 10
VALID_SCOPES = ("session", "user", "task")


def _load_json_file(path: Path) -> dict:
    try:
        if path.exists():
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else {}
    except Exception as e:
        log.debug("Failed to read %s: %s", path, e)
    return {}


def _project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))


def discover_engine_config() -> Optional[dict]:
    """Returns {api_key, task_id, base_url} or None if the tracer is not configured.

    Mirrors claude_code_tracer.discover_config so both hooks read the same
    credentials; base_url is the /api/v1 root derived from the trace endpoint.
    """
    api_key = os.environ.get("GENAI_ENGINE_API_KEY", "")
    task_id = os.environ.get("GENAI_ENGINE_TASK_ID", "")
    endpoint = os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT", "")

    for cfg_path in (
        _project_dir() / ".claude" / "arthur_config.json",
        Path.home() / ".claude" / "arthur_config.json",
    ):
        if api_key and task_id and endpoint:
            break
        cfg = _load_json_file(cfg_path)
        api_key = api_key or cfg.get("api_key", "")
        task_id = task_id or cfg.get("task_id", "")
        endpoint = endpoint or cfg.get("endpoint", "")

    if not (api_key and task_id and endpoint):
        return None

    return {"api_key": api_key, "task_id": task_id, "base_url": api_base_url(endpoint)}


def api_base_url(trace_endpoint: str) -> str:
    """'https://host/api/v1/traces' -> 'https://host/api/v1'."""
    base = trace_endpoint.rstrip("/")
    if base.endswith("/traces"):
        base = base[: -len("/traces")]
    return base


def load_breaker_config() -> dict:
    """DEFAULT_CONFIG overlaid with the first breaker config file found."""
    candidates = []
    if os.environ.get(CONFIG_ENV):
        candidates.append(Path(os.environ[CONFIG_ENV]))
    candidates.append(_project_dir() / ".claude" / "arthur_circuit_breaker.json")
    candidates.append(Path.home() / ".claude" / "arthur_circuit_breaker.json")

    config = json.loads(json.dumps(DEFAULT_CONFIG))
    for path in candidates:
        overrides = _load_json_file(path)
        if overrides:
            config.update(overrides)
            break

    if os.environ.get("ARTHUR_BREAKER_SCOPE"):
        config["scope"] = os.environ["ARTHUR_BREAKER_SCOPE"]
    if os.environ.get("ARTHUR_BREAKER_BUDGET_USD"):
        config["budget_usd"] = float(os.environ["ARTHUR_BREAKER_BUDGET_USD"])

    if config["scope"] not in VALID_SCOPES:
        log.warning("Unknown scope %r, using 'session'", config["scope"])
        config["scope"] = "session"
    return config


def _username() -> str:
    # Same fallback chain the tracer uses for the user.id span attribute.
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


# ---------------------------------------------------------------------------
# Engine client (stdlib only so the hook has no dependencies of its own)
# ---------------------------------------------------------------------------


class EngineError(Exception):
    """The engine could not be queried; the caller decides fail-open/closed."""


def _request(
    engine: dict,
    method: str,
    path: str,
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    timeout: float = 5.0,
) -> dict:
    url = f"{engine['base_url']}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {engine['api_key']}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = ""
        with contextlib.suppress(Exception):
            detail = e.read().decode()[:200]
        raise EngineError(f"HTTP {e.code} from {method} {path}: {detail}") from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise EngineError(f"{method} {path} failed: {e}") from e


def _iso_utc(dt: datetime) -> str:
    # Same shape the engine UI sends (JavaScript toISOString()).
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_engine_time(value: str) -> datetime:
    """Engine timestamps come back naive; they are stored as the server's local
    time, which is UTC on every supported deployment."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class LLMSpan:
    # The span's end: the cost is realised when the response completes, so
    # that is the moment it is bucketed at.
    end: datetime
    cost: Optional[float]
    tokens: int
    prompt_tokens: int = 0
    completion_tokens: int = 0


# The engine filters spans by start_time; a span that started before the
# window but finished inside it still belongs to it, so fetch this much extra.
SPAN_FETCH_SLACK = timedelta(minutes=15)


def _scope_params(engine: dict, scope: str, session_id: str) -> dict:
    params: dict[str, Any] = {"task_ids": engine["task_id"]}
    if scope == "session":
        params["session_ids"] = session_id
    elif scope == "user":
        params["user_ids"] = _username()
    return params


def _row_matches_scope(row: dict, scope: str) -> bool:
    # The engine's user_ids filter is a case-insensitive substring match, so
    # keep only this user's rows.
    return scope != "user" or row.get("user_id") == _username()


def _paged(engine: dict, path: str, params: dict, key: str, timeout: float):
    """Yield rows of a paginated list endpoint, up to SPAN_MAX_PAGES pages."""
    params = dict(params, page_size=SPAN_PAGE_SIZE)
    for page in range(SPAN_MAX_PAGES):
        params["page"] = page
        rows = _request(engine, "GET", path, params=params, timeout=timeout).get(
            key,
            [],
        )
        yield from rows
        if len(rows) < SPAN_PAGE_SIZE:
            break


def fetch_llm_spans(
    engine: dict,
    scope: str,
    session_id: str,
    since: datetime,
    now: datetime,
    timeout: float,
) -> list[LLMSpan]:
    """LLM spans that ended in [since, now] for the scope."""
    params = _scope_params(engine, scope, session_id)
    params.update(
        {
            "span_types": "LLM",
            "start_time": _iso_utc(since - SPAN_FETCH_SLACK),
            "end_time": _iso_utc(now),
            "sort": "desc",
            "sort_by": "start_time",
        },
    )
    spans: list[LLMSpan] = []
    for row in _paged(engine, "/traces/spans", params, "spans", timeout):
        end = row.get("end_time") or row.get("start_time")
        if not end or not _row_matches_scope(row, scope):
            continue
        spans.append(
            LLMSpan(
                end=parse_engine_time(end),
                cost=row.get("total_token_cost"),
                tokens=int(row.get("total_token_count") or 0),
                prompt_tokens=int(row.get("prompt_token_count") or 0),
                completion_tokens=int(row.get("completion_token_count") or 0),
            ),
        )
    return spans


def fetch_scope_total(
    engine: dict,
    scope: str,
    session_id: str,
    period_start: datetime,
    now: datetime,
    timeout: float,
) -> float:
    """Total spend the hard cap applies to: the whole session, or the budget
    period for user/task scope."""
    if scope == "session":
        payload = _request(
            engine,
            "GET",
            "/traces/sessions",
            params={
                "task_ids": engine["task_id"],
                "session_ids": session_id,
                "page_size": 1,
            },
            timeout=timeout,
        )
        sessions = payload.get("sessions", [])
        return float((sessions[0].get("total_token_cost") or 0.0) if sessions else 0.0)

    if scope == "user":
        # No endpoint gives one user's spend over a time window (the users
        # list cannot filter by user and the user detail is all-time), so sum
        # this user's traces in the period instead.
        params = _scope_params(engine, scope, session_id)
        params.update(
            {
                "start_time": _iso_utc(period_start),
                "end_time": _iso_utc(now),
                "sort": "desc",
            },
        )
        return sum(
            float(row.get("total_token_cost") or 0.0)
            for row in _paged(engine, "/traces", params, "traces", timeout)
            if _row_matches_scope(row, scope)
        )

    payload = _request(
        engine,
        "POST",
        "/traces/overview",
        body={
            "task_ids": [engine["task_id"]],
            "start_time": _iso_utc(period_start),
            "end_time": _iso_utc(now),
        },
        timeout=timeout,
    )
    overviews = payload.get("overviews", [])
    return float(overviews[0].get("trace_token_cost") or 0.0) if overviews else 0.0


# ---------------------------------------------------------------------------
# Burn-rate evaluation
# ---------------------------------------------------------------------------


@dataclass
class RuleResult:
    name: str
    window_minutes: float
    short_window_minutes: Optional[float]
    threshold: float
    window_spend: float
    window_burn_rate: float
    short_spend: Optional[float]
    short_burn_rate: Optional[float]

    @property
    def effective_burn_rate(self) -> float:
        """The burn rate the rule is judged on: the lower of the two windows,
        since both must exceed the threshold for the rule to fire."""
        if self.short_burn_rate is None:
            return self.window_burn_rate
        return min(self.window_burn_rate, self.short_burn_rate)

    @property
    def fired(self) -> bool:
        return self.effective_burn_rate >= self.threshold

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "window_minutes": self.window_minutes,
            "short_window_minutes": self.short_window_minutes,
            "threshold": self.threshold,
            "window_spend_usd": round(self.window_spend, 4),
            "window_burn_rate": round(self.window_burn_rate, 2),
            "short_spend_usd": (
                None if self.short_spend is None else round(self.short_spend, 4)
            ),
            "short_burn_rate": (
                None if self.short_burn_rate is None else round(self.short_burn_rate, 2)
            ),
            "fired": self.fired,
        }


@dataclass
class Evaluation:
    tripped: bool
    reason: str = ""
    warning: str = ""
    rules: list[RuleResult] = field(default_factory=list)
    scope_total_usd: Optional[float] = None
    unpriced_spans: int = 0
    unpriced_tokens: int = 0
    engine_error: str = ""

    def to_dict(self) -> dict:
        return {
            "tripped": self.tripped,
            "reason": self.reason,
            "warning": self.warning,
            "rules": [r.to_dict() for r in self.rules],
            "scope_total_usd": self.scope_total_usd,
            "unpriced_spans": self.unpriced_spans,
            "unpriced_tokens": self.unpriced_tokens,
            "engine_error": self.engine_error,
        }


def span_cost(span: LLMSpan, fallback_rates: Optional[dict]) -> Optional[float]:
    """The span's cost, priced locally when the engine could not price it."""
    if span.cost is not None:
        return float(span.cost)
    if span.tokens == 0:
        return 0.0
    if not fallback_rates:
        return None
    prompt_rate = float(fallback_rates.get("prompt", 0.0))
    completion_rate = float(fallback_rates.get("completion", 0.0))
    if span.prompt_tokens or span.completion_tokens:
        return (
            span.prompt_tokens * prompt_rate + span.completion_tokens * completion_rate
        ) / 1_000_000
    return span.tokens * prompt_rate / 1_000_000


def window_spend(
    spans: list[LLMSpan],
    now: datetime,
    minutes: float,
    fallback_rates: Optional[dict],
) -> float:
    cutoff = now - timedelta(minutes=minutes)
    return sum(span_cost(s, fallback_rates) or 0.0 for s in spans if s.end >= cutoff)


def burn_rate(spend_usd: float, minutes: float, config: dict) -> float:
    budget = float(config["budget_usd"])
    period_hours = float(config["budget_period_hours"])
    if budget <= 0 or period_hours <= 0 or minutes <= 0:
        return 0.0
    return (spend_usd / (minutes / 60.0)) / (budget / period_hours)


def evaluate_rules(
    spans: list[LLMSpan],
    now: datetime,
    config: dict,
) -> list[RuleResult]:
    fallback = config.get("fallback_usd_per_million_tokens")
    results = []
    for rule in config["rules"]:
        minutes = float(rule["window_minutes"])
        spend = window_spend(spans, now, minutes, fallback)
        short_minutes = rule.get("short_window_minutes")
        short_spend = short_rate = None
        if short_minutes:
            short_minutes = float(short_minutes)
            short_spend = window_spend(spans, now, short_minutes, fallback)
            short_rate = burn_rate(short_spend, short_minutes, config)
        results.append(
            RuleResult(
                name=rule.get("name", f"{int(minutes)}m"),
                window_minutes=minutes,
                short_window_minutes=short_minutes,
                threshold=float(rule["burn_rate"]),
                window_spend=spend,
                window_burn_rate=burn_rate(spend, minutes, config),
                short_spend=short_spend,
                short_burn_rate=short_rate,
            ),
        )
    return results


def _describe_rule(r: RuleResult, config: dict) -> str:
    budget = (
        f"${float(config['budget_usd']):.2f}/{float(config['budget_period_hours']):g}h"
    )
    per_hour = r.window_spend / (r.window_minutes / 60.0) if r.window_minutes else 0.0
    text = (
        f"{r.name}: ${r.window_spend:.2f} in the last {r.window_minutes:g}m "
        f"(${per_hour:.2f}/h) is {r.window_burn_rate:.1f}x the budget rate ({budget})"
    )
    if r.short_burn_rate is not None:
        text += (
            f"; last {r.short_window_minutes:g}m: ${r.short_spend:.2f} "
            f"({r.short_burn_rate:.1f}x)"
        )
    return text


def evaluate(
    engine: dict,
    config: dict,
    session_id: str,
    now: Optional[datetime] = None,
) -> Evaluation:
    """Query the engine and decide whether the breaker should be open."""
    now = now or datetime.now(timezone.utc)
    scope = config["scope"]
    timeout = float(config.get("http_timeout_seconds", 5))
    rules = config.get("rules") or []
    max_minutes = max((float(r["window_minutes"]) for r in rules), default=0.0)

    try:
        spans: list[LLMSpan] = []
        if rules:  # a hard-cap-only config has no windows to fill
            spans = fetch_llm_spans(
                engine,
                scope,
                session_id,
                since=now - timedelta(minutes=max_minutes),
                now=now,
                timeout=timeout,
            )
        scope_total = None
        if config.get("hard_cap_usd") is not None:
            scope_total = fetch_scope_total(
                engine,
                scope,
                session_id,
                period_start=now
                - timedelta(hours=float(config["budget_period_hours"])),
                now=now,
                timeout=timeout,
            )
    except EngineError as e:
        fail_closed = config.get("fail_mode") == "closed"
        return Evaluation(
            tripped=fail_closed,
            reason=(
                f"Arthur Engine unreachable and fail_mode is closed: {e}"
                if fail_closed
                else ""
            ),
            warning=(
                ""
                if fail_closed
                else f"Arthur circuit breaker could not reach the engine (failing open): {e}"
            ),
            engine_error=str(e),
        )

    fallback = config.get("fallback_usd_per_million_tokens")
    unpriced = [s for s in spans if span_cost(s, fallback) is None]
    rules = evaluate_rules(spans, now, config)
    result = Evaluation(
        tripped=False,
        rules=rules,
        scope_total_usd=scope_total,
        unpriced_spans=len(unpriced),
        unpriced_tokens=sum(s.tokens for s in unpriced),
    )

    fired = [r for r in rules if r.fired]
    if fired:
        worst = max(fired, key=lambda r: r.effective_burn_rate / r.threshold)
        result.tripped = True
        result.reason = _describe_rule(worst, config)
        return result

    cap = config.get("hard_cap_usd")
    if cap is not None and scope_total is not None and scope_total >= float(cap):
        result.tripped = True
        result.reason = (
            f"hard cap: ${scope_total:.2f} spent in {scope} scope "
            f"meets the ${float(cap):.2f} ceiling"
        )
        return result

    warn_fraction = float(config.get("warn_fraction", 0.75))
    warnings = []
    for r in rules:
        if r.threshold and r.effective_burn_rate >= warn_fraction * r.threshold:
            warnings.append(
                f"{_describe_rule(r, config)} — trips at {r.threshold:g}x",
            )
    if (
        cap is not None
        and scope_total is not None
        and scope_total >= warn_fraction * float(cap)
    ):
        warnings.append(
            f"${scope_total:.2f} of the ${float(cap):.2f} {scope} hard cap spent",
        )
    if unpriced and not fallback:
        warnings.append(
            f"{len(unpriced)} LLM span(s) / {result.unpriced_tokens} tokens have no "
            "cost (model not priced by the engine); set fallback_usd_per_million_tokens "
            "so the breaker can see them",
        )
    if warnings:
        result.warning = "Arthur circuit breaker: " + "; ".join(warnings)
    return result


# ---------------------------------------------------------------------------
# Breaker state (persisted so every hook invocation shares one verdict)
# ---------------------------------------------------------------------------

STATUS_CLOSED = "closed"
STATUS_OPEN = "open"


def state_key(engine: dict, config: dict, session_id: str) -> str:
    scope = config["scope"]
    parts = [scope, engine["task_id"]]
    if scope == "session":
        parts.append(session_id)
    elif scope == "user":
        parts.append(_username())
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def _state_path(key: str) -> Path:
    return STATE_DIR / f"{key}.json"


def load_state(key: str) -> dict:
    return _load_json_file(_state_path(key))


def save_state(key: str, state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        _state_path(key).write_text(json.dumps(state))
    except OSError as e:
        log.warning("Failed to save breaker state: %s", e)
    _prune_stale_state(exclude=key)


def _prune_stale_state(exclude: str, now_ts: Optional[float] = None) -> None:
    """Drop state and lock files untouched for STATE_MAX_AGE_S (session-scope
    keys are created per Claude Code session and never revisited)."""
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    try:
        for p in STATE_DIR.iterdir():
            if p.stem == exclude or p.suffix not in (".json", ".lock"):
                continue
            with contextlib.suppress(OSError):
                if now_ts - p.stat().st_mtime > STATE_MAX_AGE_S:
                    p.unlink()
    except OSError as e:
        log.debug("Failed to prune breaker state: %s", e)


def clear_state() -> int:
    removed = 0
    if STATE_DIR.exists():
        for p in STATE_DIR.glob("*.json"):
            with contextlib.suppress(OSError):
                p.unlink()
                removed += 1
    return removed


@contextlib.contextmanager
def _state_lock(key: str):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = STATE_DIR / f"{key}.lock"
    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


@dataclass
class Verdict:
    tripped: bool
    message: str = ""  # shown when tripped
    warning: str = ""  # shown when not tripped, only on a fresh check
    fresh: bool = False  # True when the engine was queried this invocation


def _reset_hint() -> str:
    return f'reset with: python3 "{Path(__file__).resolve()}" reset'


def decide(
    engine: dict,
    config: dict,
    session_id: str,
    now: Optional[datetime] = None,
) -> Verdict:
    """Run the breaker state machine for one hook invocation.

    closed  -> allow; re-check the engine once per check_interval_seconds
    open    -> block without querying until cooldown_minutes have passed
    half-open (cooldown over) -> probe the engine; close if calm, else re-open
    """
    now = now or datetime.now(timezone.utc)
    now_ts = now.timestamp()
    key = state_key(engine, config, session_id)
    cooldown_s = float(config.get("cooldown_minutes", 15)) * 60
    interval_s = float(config.get("check_interval_seconds", 30))

    with _state_lock(key):
        state = load_state(key)
        status = state.get("status", STATUS_CLOSED)

        if status == STATUS_OPEN:
            opened_at = float(state.get("opened_at", 0))
            if now_ts - opened_at < cooldown_s:
                return Verdict(
                    tripped=True,
                    message=_open_message(state, config, now_ts),
                )
            # Cooldown elapsed: half-open probe.
            evaluation = evaluate(engine, config, session_id, now)
            if evaluation.engine_error and not evaluation.tripped:
                # Nothing was measured, so stay open and probe again on the
                # next hook rather than declare the spend calm.
                state["last_check_at"] = now_ts
                state["last_evaluation"] = evaluation.to_dict()
                save_state(key, state)
                return Verdict(
                    tripped=True,
                    message=_open_message(state, config, now_ts)
                    + f" (re-check failed: {evaluation.engine_error})",
                    fresh=True,
                )
            if evaluation.tripped:
                state.update(
                    status=STATUS_OPEN,
                    opened_at=now_ts,
                    reason=evaluation.reason,
                    last_check_at=now_ts,
                    last_evaluation=evaluation.to_dict(),
                )
                save_state(key, state)
                return Verdict(
                    tripped=True,
                    message=_open_message(state, config, now_ts),
                    fresh=True,
                )
            state = {
                "status": STATUS_CLOSED,
                "last_check_at": now_ts,
                "last_evaluation": evaluation.to_dict(),
            }
            save_state(key, state)
            return Verdict(
                tripped=False,
                warning="Arthur circuit breaker closed again: spend is back under the burn-rate threshold."
                + (f" {evaluation.warning}" if evaluation.warning else ""),
                fresh=True,
            )

        last_check = float(state.get("last_check_at", 0))
        if now_ts - last_check < interval_s and state.get("last_evaluation"):
            return Verdict(tripped=False)

        evaluation = evaluate(engine, config, session_id, now)
        if evaluation.tripped:
            state = {
                "status": STATUS_OPEN,
                "opened_at": now_ts,
                "reason": evaluation.reason,
                "last_check_at": now_ts,
                "last_evaluation": evaluation.to_dict(),
            }
            save_state(key, state)
            return Verdict(
                tripped=True,
                message=_open_message(state, config, now_ts),
                fresh=True,
            )

        state = {
            "status": STATUS_CLOSED,
            "last_check_at": now_ts,
            "last_evaluation": evaluation.to_dict(),
        }
        save_state(key, state)
        return Verdict(tripped=False, warning=evaluation.warning, fresh=True)


def _open_message(state: dict, config: dict, now_ts: float) -> str:
    cooldown_s = float(config.get("cooldown_minutes", 15)) * 60
    retry_at = datetime.fromtimestamp(
        float(state.get("opened_at", now_ts)) + cooldown_s,
    ).strftime("%H:%M")
    return (
        f"Arthur circuit breaker OPEN ({config['scope']} scope) — {state.get('reason', '')}. "
        f"Claude Code is paused until {retry_at} (it re-checks the engine then), "
        f"or {_reset_hint()}"
    )


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


def hook_output(event: str, verdict: Verdict) -> Optional[dict]:
    """The JSON Claude Code expects on stdout for this event, or None for silence."""
    if verdict.tripped:
        if event == "user_prompt_submit":
            return {
                "decision": "block",
                "reason": verdict.message,
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "suppressOriginalPrompt": True,
                },
            }
        if event == "pre_tool":
            # Denying alone would let the turn keep calling the model with the
            # tool error; continue=false ends the turn outright.
            return {
                "continue": False,
                "stopReason": verdict.message,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": verdict.message,
                },
            }
        if event == "session_start":
            return {"systemMessage": verdict.message}
        return None

    if verdict.warning and verdict.fresh:
        return {"systemMessage": verdict.warning}
    return None


def run_hook(event: str, data: dict) -> Optional[dict]:
    if os.environ.get(BYPASS_ENV, "").lower() in ("1", "true", "yes"):
        return None
    engine = discover_engine_config()
    if engine is None:
        log.debug("Arthur Engine not configured, skipping circuit breaker.")
        return None
    config = load_breaker_config()
    if not config.get("enabled", True):
        return None
    session_id = data.get("session_id", "unknown")
    verdict = decide(engine, config, session_id)
    return hook_output(event, verdict)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cli_status(args: list[str]) -> int:
    engine = discover_engine_config()
    if engine is None:
        print(
            "Arthur Engine not configured (no api_key/task_id/endpoint).",
            file=sys.stderr,
        )
        return 1
    config = load_breaker_config()
    session_id = "unknown"
    if "--session" in args:
        idx = args.index("--session") + 1
        if idx >= len(args):
            print("usage: status [--session SESSION_ID]", file=sys.stderr)
            return 2
        session_id = args[idx]
    elif config["scope"] == "session":
        print(
            "scope is 'session' but no --session ID given; evaluating task-wide instead",
            file=sys.stderr,
        )
        config["scope"] = "task"
    evaluation = evaluate(engine, config, session_id)
    state = load_state(state_key(engine, config, session_id))
    print(
        json.dumps(
            {
                "scope": config["scope"],
                "budget_usd": config["budget_usd"],
                "budget_period_hours": config["budget_period_hours"],
                "breaker_status": state.get("status", STATUS_CLOSED),
                "evaluation": evaluation.to_dict(),
            },
            indent=2,
        ),
    )
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: claude_code_circuit_breaker.py <user_prompt_submit|pre_tool|session_start|status|reset>",
            file=sys.stderr,
        )
        sys.exit(0)

    command = sys.argv[1]
    if command == "reset":
        print(f"Cleared {clear_state()} breaker state file(s); breaker is closed.")
        sys.exit(0)
    if command == "status":
        sys.exit(cli_status(sys.argv[2:]))

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        log.warning("Failed to parse stdin JSON: %s", e)
        data = {}

    if command not in ("user_prompt_submit", "pre_tool", "session_start"):
        log.warning("Unknown event: %s", command)
        sys.exit(0)

    output = None
    try:
        output = run_hook(command, data)
    except Exception as e:
        # Never let a breaker bug block the user's session.
        log.warning("Circuit breaker error (%s): %s", command, e, exc_info=True)

    if output is not None:
        print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
