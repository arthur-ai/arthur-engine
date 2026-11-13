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
  check                  — verify the key can read spend and the engine's clock
                           reads right (install.sh runs it)
  reset                  — close the breaker (clears persisted state)

Override from inside Claude Code: an open breaker blocks every prompt, so a
prompt that *starts with* "breaker override" (or "override the breaker",
optionally "for 45m" / "for 2h") lifts the breaker for override_minutes. The
override prompt itself is consumed, not sent to Claude, so Claude does not take
it as a cue to resume the work the breaker just stopped. That is the way out
when you cannot reach a shell; otherwise use the reset CLI or wait for the
cooldown.

Engine credentials come from the same place the tracer reads them (env vars,
then <project>/.claude/arthur_config.json, then ~/.claude/arthur_config.json).
Reading spend needs a key with read access to traces, which a tracing key often
lacks, so GENAI_ENGINE_READ_API_KEY / read_api_key take precedence over the
tracer's api_key. Breaker settings come from ARTHUR_BREAKER_CONFIG, then
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
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

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
    # The spend budget and the period it is meant to last. A null budget_usd
    # takes the scope's default from SCOPE_BUDGET_USD; task scope has none.
    "budget_usd": None,
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
    # Arthur Engine stamps spans in its server's local time with no offset:
    # "UTC" for the container images, "local" for an engine running on this
    # machine outside a container, or an IANA name like "America/Los_Angeles".
    "engine_timezone": "UTC",
    # Spans whose model Arthur Engine could not price carry no cost. These
    # per-million-token rates fill the gap so the breaker is not blind to
    # them; null leaves such spans at $0 and warns instead.
    "fallback_usd_per_million_tokens": None,
    # How long a "breaker override" prompt keeps the breaker lifted when it
    # does not name a duration itself.
    "override_minutes": 30,
}

# The budget for a null budget_usd. These are generous on purpose: by default
# the breaker is there to stop a runaway, not to enforce a budget, and a trip
# on ordinary work is what gets it switched off. A user's parallel sessions
# share theirs, so it is three sessions' worth. A task's depends on the size of
# the team sharing it, so task scope has no default and its burn-rate rules
# stay off until it is set.
SCOPE_BUDGET_USD = {"session": 200.0, "user": 600.0}

CONFIG_ENV = "ARTHUR_BREAKER_CONFIG"
BYPASS_ENV = "ARTHUR_BREAKER_BYPASS"
STATE_DIR = Path.home() / ".claude" / "circuit_breaker"
STATE_MAX_AGE_S = 48 * 3600
# Every engine call one hook makes shares this budget, kept under the 15 s
# hook timeout install.sh registers so paging cannot get the hook killed.
QUERY_BUDGET_S = 10.0
# List rows carry span content, so pages start small and double (50, 50, 100,
# 200 ...) up to SPAN_MAX_PAGE_SIZE: a quiet window costs one small request.
SPAN_FIRST_PAGE_SIZE = 50
SPAN_MAX_PAGE_SIZE = 800
SPAN_MAX_ROWS = 20_000
VALID_SCOPES = ("session", "user", "task")
READ_KEY_HINT = (
    "Reading spend needs an API key with read access to traces (role "
    "ORG-AUDITOR, TASK-ADMIN, TENANT-USER or ORG-ADMIN); a tracing key often "
    "only has write access. Set read_api_key in arthur_config.json or "
    "GENAI_ENGINE_READ_API_KEY."
)


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
    """Returns {api_key, key_name, task_id, base_url} or None if the tracer is
    not configured.

    Mirrors claude_code_tracer.discover_config so both hooks read the same
    credentials; base_url is the /api/v1 root derived from the trace endpoint.
    The tracer's key only needs to write traces, so a read_api_key, wherever
    it is set, is used in its place; key_name says which one is in use.
    """
    api_key = os.environ.get("GENAI_ENGINE_API_KEY", "")
    read_key = os.environ.get("GENAI_ENGINE_READ_API_KEY", "")
    task_id = os.environ.get("GENAI_ENGINE_TASK_ID", "")
    endpoint = os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT", "")

    for cfg_path in (
        _project_dir() / ".claude" / "arthur_config.json",
        Path.home() / ".claude" / "arthur_config.json",
    ):
        if read_key and task_id and endpoint:
            break
        cfg = _load_json_file(cfg_path)
        api_key = api_key or cfg.get("api_key", "")
        read_key = read_key or cfg.get("read_api_key", "")
        task_id = task_id or cfg.get("task_id", "")
        endpoint = endpoint or cfg.get("endpoint", "")

    if not ((read_key or api_key) and task_id and endpoint):
        return None

    return {
        "api_key": read_key or api_key,
        "key_name": "read_api_key" if read_key else "api_key",
        "task_id": task_id,
        "base_url": api_base_url(endpoint),
    }


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
        try:
            config["budget_usd"] = float(os.environ["ARTHUR_BREAKER_BUDGET_USD"])
        except ValueError:
            log.warning(
                "Ignoring non-numeric ARTHUR_BREAKER_BUDGET_USD=%r",
                os.environ["ARTHUR_BREAKER_BUDGET_USD"],
            )

    if config["scope"] not in VALID_SCOPES:
        log.warning("Unknown scope %r, using 'session'", config["scope"])
        config["scope"] = "session"
    # A bad budget must not disable the breaker: fall back to the default
    # rather than let a ValueError/ZeroDivisionError fail every hook open.
    for key in ("budget_usd", "budget_period_hours"):
        if key == "budget_usd" and config[key] is None:
            continue  # the scope's default
        try:
            value = float(config[key])
        except (TypeError, ValueError):
            value = 0.0
        if value <= 0:
            log.warning(
                "%s must be a positive number, got %r; using %s",
                key,
                config[key],
                (
                    "the scope's default"
                    if DEFAULT_CONFIG[key] is None
                    else DEFAULT_CONFIG[key]
                ),
            )
            config[key] = DEFAULT_CONFIG[key]
    try:
        _engine_zone(config)
    except (KeyError, ValueError, TypeError):
        log.warning(
            "Unknown engine_timezone %r, using 'UTC'",
            config.get("engine_timezone"),
        )
        config["engine_timezone"] = "UTC"
    return config


def budget_usd(config: dict) -> Optional[float]:
    """The budget the burn rate is measured against: budget_usd, or the
    scope's default when it is null. None for task scope with none set."""
    value = config.get("budget_usd")
    if value is None:
        return SCOPE_BUDGET_USD.get(config.get("scope", "session"))
    return float(value)


def config_problem(config: dict) -> str:
    """A setting that keeps the breaker from working, as a message, or ""."""
    if budget_usd(config) is None and config.get("rules"):
        return (
            f"scope is {config.get('scope')} but budget_usd is not set, so the "
            "burn-rate rules are off (hard_cap_usd still applies); set budget_usd "
            "in arthur_circuit_breaker.json to what the whole task may spend per "
            "budget_period_hours"
        )
    return ""


def _username() -> str:
    # Same fallback chain the tracer uses for the user.id span attribute.
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


# ---------------------------------------------------------------------------
# Engine client (stdlib only so the hook has no dependencies of its own)
# ---------------------------------------------------------------------------


class EngineError(Exception):
    """The engine could not be queried; the caller decides fail-open/closed."""


class EngineAuthError(EngineError):
    """The engine refused the key (HTTP 401/403): a configuration problem, not
    an outage, so it is reported with what to fix."""


class Deadline:
    """Time left for the engine calls of one hook, so paging cannot outlast
    the hook timeout. Each request gets at most http_timeout_seconds of it."""

    def __init__(self, seconds: Optional[float] = None):
        self.end = time.monotonic() + (QUERY_BUDGET_S if seconds is None else seconds)

    def remaining(self) -> float:
        return self.end - time.monotonic()

    def timeout(self, per_request: float) -> float:
        left = self.remaining()
        if left <= 0:
            raise EngineError(f"no reply within the {QUERY_BUDGET_S:g}s query budget")
        return min(per_request, left)


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
        message = f"HTTP {e.code} from {method} {path}: {detail}"
        if e.code in (401, 403):
            raise EngineAuthError(
                f"{message} (using {engine.get('key_name', 'api_key')})",
            ) from e
        raise EngineError(message) from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise EngineError(f"{method} {path} failed: {e}") from e


# ---------------------------------------------------------------------------
# Engine timestamps
#
# The engine converts span times to its server's local time and stores and
# returns them without an offset, and it compares time filters against those
# naive values. engine_timezone names that zone, so times are read and sent
# in it.
# ---------------------------------------------------------------------------


def _engine_zone(config: Optional[dict]) -> Optional[tzinfo]:
    """The zone engine timestamps are in; None means this machine's zone."""
    name = str((config or {}).get("engine_timezone") or "UTC")
    if name.lower() == "local":
        return None
    if name.upper() == "UTC":
        return timezone.utc
    return ZoneInfo(name)


def parse_engine_time(value: str, config: Optional[dict] = None) -> datetime:
    """An engine timestamp as an aware UTC datetime."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        zone = _engine_zone(config)
        # astimezone() on a naive datetime reads it as this machine's time.
        dt = dt.replace(tzinfo=zone) if zone else dt.astimezone()
    return dt.astimezone(timezone.utc)


def _engine_time_param(dt: datetime, config: dict) -> str:
    """A time filter value in the engine's zone, without an offset, so the
    database compares it with the stored values as they are."""
    return dt.astimezone(_engine_zone(config)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


@dataclass
class LLMSpan:
    # The span's end: the cost is realised when the response completes, so
    # that is the moment it is bucketed at.
    end: datetime
    cost: Optional[float]
    tokens: int
    prompt_tokens: int = 0
    completion_tokens: int = 0


# Spans are fetched by start time; one that started before the window but
# finished inside it still belongs to it, so read this much further back.
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


def _paged(
    engine: dict,
    path: str,
    params: dict,
    key: str,
    config: dict,
    deadline: Deadline,
    id_field: str,
    stop: Optional[Callable[[dict], bool]] = None,
) -> tuple[list[dict], bool]:
    """Rows of a paginated list endpoint, plus whether they were cut off
    (SPAN_MAX_ROWS or the query budget reached with more to read).

    Pages run 50, 50, 100, 200 ... rows, so each offset is a multiple of the
    next page size and the pages tile the list. Paging ends early once
    stop(last row of a page) is true. Rows that a concurrent insert pushed
    onto the next page are dropped by id_field.
    """
    per_request = float(config.get("http_timeout_seconds", 5))
    rows: list[dict] = []
    seen: set = set()
    offset, size = 0, SPAN_FIRST_PAGE_SIZE
    while len(rows) < SPAN_MAX_ROWS:
        if offset and deadline.remaining() <= 0:
            return rows, True
        page_rows = _request(
            engine,
            "GET",
            path,
            params=dict(params, page=offset // size, page_size=size),
            timeout=deadline.timeout(per_request),
        ).get(key, [])
        for row in page_rows:
            row_id = row.get(id_field)
            if row_id is not None:
                if row_id in seen:
                    continue
                seen.add(row_id)
            rows.append(row)
        if len(page_rows) < size or (stop and page_rows and stop(page_rows[-1])):
            return rows, False
        offset += size
        size = min(offset, SPAN_MAX_PAGE_SIZE)
    return rows, True


def fetch_llm_spans(
    engine: dict,
    config: dict,
    session_id: str,
    since: datetime,
    deadline: Deadline,
) -> tuple[list[LLMSpan], bool]:
    """LLM spans that ended at or after `since` for the scope, and whether the
    engine had more than could be read.

    The engine's start_time/end_time filters apply to the *trace*, and a trace
    is a whole turn: one that started before the window (a long autonomous
    turn, the runaway case) would drop out entirely. So spans are read newest
    first by their own start time, unfiltered, until a page reaches spans that
    started before the window, and are bucketed here.
    """
    scope = config["scope"]
    params = _scope_params(engine, scope, session_id)
    params.update({"span_types": "LLM", "sort": "desc", "sort_by": "start_time"})
    cutoff = since - SPAN_FETCH_SLACK

    def before_window(row: dict) -> bool:
        start = row.get("start_time")
        return bool(start) and parse_engine_time(start, config) < cutoff

    rows, truncated = _paged(
        engine,
        "/traces/spans",
        params,
        "spans",
        config,
        deadline,
        id_field="id",
        stop=before_window,
    )
    spans: list[LLMSpan] = []
    for row in rows:
        end = row.get("end_time") or row.get("start_time")
        if not end or not _row_matches_scope(row, scope):
            continue
        end_at = parse_engine_time(end, config)
        if end_at < since:
            continue
        spans.append(
            LLMSpan(
                end=end_at,
                cost=row.get("total_token_cost"),
                tokens=int(row.get("total_token_count") or 0),
                prompt_tokens=int(row.get("prompt_token_count") or 0),
                completion_tokens=int(row.get("completion_token_count") or 0),
            ),
        )
    return spans, truncated


def fetch_scope_total(
    engine: dict,
    config: dict,
    session_id: str,
    period_start: datetime,
    now: datetime,
    deadline: Deadline,
) -> tuple[float, bool]:
    """Total spend the hard cap applies to: the whole session, or the budget
    period for user/task scope. Plus whether it was cut off (only the user
    scope pages), which makes the total a lower bound."""
    scope = config["scope"]
    per_request = float(config.get("http_timeout_seconds", 5))
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
            timeout=deadline.timeout(per_request),
        )
        sessions = payload.get("sessions", [])
        total = (sessions[0].get("total_token_cost") or 0.0) if sessions else 0.0
        return float(total), False

    if scope == "user":
        # No endpoint gives one user's spend over a time window (the users
        # list cannot filter by user and the user detail is all-time), so sum
        # this user's traces in the period instead.
        params = _scope_params(engine, scope, session_id)
        params.update(
            {
                "start_time": _engine_time_param(period_start, config),
                "end_time": _engine_time_param(now, config),
                "sort": "desc",
            },
        )
        rows, truncated = _paged(
            engine,
            "/traces",
            params,
            "traces",
            config,
            deadline,
            id_field="trace_id",
        )
        total = sum(
            float(row.get("total_token_cost") or 0.0)
            for row in rows
            if _row_matches_scope(row, scope)
        )
        return total, truncated

    payload = _request(
        engine,
        "POST",
        "/traces/overview",
        body={
            "task_ids": [engine["task_id"]],
            "start_time": _engine_time_param(period_start, config),
            "end_time": _engine_time_param(now, config),
        },
        timeout=deadline.timeout(per_request),
    )
    overviews = payload.get("overviews", [])
    total = (overviews[0].get("trace_token_cost") or 0.0) if overviews else 0.0
    return float(total), False


# ---------------------------------------------------------------------------
# Startup check: can the key read spend, and do the engine's timestamps read
# right? Run by SessionStart and the check CLI, where a wrong answer would
# otherwise only show up as a breaker that never trips.
# ---------------------------------------------------------------------------

# A UTC offset is a whole number of quarter hours; ingest lag is far smaller.
_QUARTER_HOUR = timedelta(minutes=15)
_CLOCK_TOLERANCE = timedelta(minutes=10)


def _format_offset(offset: timedelta) -> str:
    minutes = round(offset.total_seconds() / 60)
    sign = "+" if minutes >= 0 else "-"
    return f"UTC{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


def _format_hours(delta: timedelta) -> str:
    return f"{abs(delta.total_seconds()) / 3600:.1f}h"


def _wall_clock(value: str) -> datetime:
    """An engine timestamp as the naive wall-clock time it was stored as."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def check_engine_clock(
    engine: dict,
    config: dict,
    deadline: Deadline,
    now: Optional[datetime] = None,
) -> str:
    """A warning when the engine's span times do not look like they are in
    engine_timezone, or "" when they look right or there is nothing to judge.

    Two signs, from the newest LLM span on the task:
      - it ends in the future: the engine is east of engine_timezone;
      - with engine_timezone UTC, its end_time (stamped by the engine) and
        created_at (stamped by the database) differ by a whole number of
        quarter hours: the engine runs on local time, as it does under
        `uv run serve` beside a containerised (UTC) Postgres.
    An engine and database that both run on local time leave no trace in
    the data; set engine_timezone to "local" for those.
    """
    now = now or datetime.now(timezone.utc)
    rows = _request(
        engine,
        "GET",
        "/traces/spans",
        params={
            "task_ids": engine["task_id"],
            "span_types": "LLM",
            "sort": "desc",
            "sort_by": "start_time",
            "page": 0,
            "page_size": 1,
        },
        timeout=deadline.timeout(float(config.get("http_timeout_seconds", 5))),
    ).get("spans", [])
    if not rows or not rows[0].get("end_time"):
        return ""
    row = rows[0]
    zone_name = config.get("engine_timezone") or "UTC"
    ahead = parse_engine_time(row["end_time"], config) - now
    if ahead > _CLOCK_TOLERANCE:
        return (
            f"the newest span on the task ends {_format_hours(ahead)} in the future "
            f'when read as engine_timezone "{zone_name}", so the engine is not on '
            "that zone and its spend would be misplaced; set engine_timezone in "
            "arthur_circuit_breaker.json to the engine server's zone"
        )
    if str(zone_name).upper() != "UTC" or not row.get("created_at"):
        return ""
    drift = _wall_clock(row["created_at"]) - _wall_clock(row["end_time"])
    quarters = round(drift / _QUARTER_HOUR)
    if abs(quarters) < 3 or abs(drift - quarters * _QUARTER_HOUR) > timedelta(
        minutes=5,
    ):
        return ""
    engine_offset = -quarters * _QUARTER_HOUR
    here = now.astimezone().utcoffset()
    fix = (
        '"local" (it matches this machine)'
        if engine_offset == here
        else f"the engine server's zone (it looks like {_format_offset(engine_offset)})"
    )
    return (
        f"Arthur Engine stamps span times {_format_hours(drift)} "
        f"{'behind' if drift > timedelta(0) else 'ahead of'} its database clock, "
        "so the engine server is probably not on UTC and the breaker would "
        f"read recent spend as hours old; set engine_timezone to {fix} in "
        "arthur_circuit_breaker.json"
    )


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
    # True when the span query hit the row cap or the query budget, so spend
    # may be under-counted.
    truncated: bool = False
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
            "truncated": self.truncated,
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
    budget = budget_usd(config) or 0.0
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
    for rule in config.get("rules") or []:
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
        f"${budget_usd(config) or 0.0:.2f}/{float(config['budget_period_hours']):g}h"
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
    deadline: Optional[Deadline] = None,
) -> Evaluation:
    """Query the engine and decide whether the breaker should be open."""
    now = now or datetime.now(timezone.utc)
    deadline = deadline or Deadline()
    scope = config["scope"]
    if budget_usd(config) is None:
        # No budget to measure a burn rate against (see config_problem).
        config = dict(config, rules=[])
    rules = config.get("rules") or []
    max_minutes = max((float(r["window_minutes"]) for r in rules), default=0.0)

    try:
        spans: list[LLMSpan] = []
        truncated = False
        if rules:  # a hard-cap-only config has no windows to fill
            spans, truncated = fetch_llm_spans(
                engine,
                config,
                session_id,
                since=now - timedelta(minutes=max_minutes),
                deadline=deadline,
            )
        scope_total = None
        cap_truncated = False
        if config.get("hard_cap_usd") is not None:
            scope_total, cap_truncated = fetch_scope_total(
                engine,
                config,
                session_id,
                period_start=now
                - timedelta(hours=float(config["budget_period_hours"])),
                now=now,
                deadline=deadline,
            )
    except EngineError as e:
        fail_closed = config.get("fail_mode") == "closed"
        if isinstance(e, EngineAuthError):
            problem = f"Arthur Engine refused the breaker's key ({e}). {READ_KEY_HINT}"
        else:
            problem = f"Arthur Engine unreachable: {e}"
        return Evaluation(
            tripped=fail_closed,
            reason=f"{problem} (fail_mode is closed)" if fail_closed else "",
            warning=(
                ""
                if fail_closed
                else f"Arthur circuit breaker cannot read spend, failing open: {problem}"
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
        truncated=truncated or cap_truncated,
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
    if truncated:
        warnings.append(
            f"could not read every LLM span in the window (over {SPAN_MAX_ROWS} "
            f"or past the {QUERY_BUDGET_S:g}s query budget); the oldest were "
            "not counted, so burn rates are a lower bound (narrow the scope or "
            "the widest window)",
        )
    if cap_truncated:
        warnings.append(
            f"could not read every trace in the budget period (over {SPAN_MAX_ROWS} "
            f"or past the {QUERY_BUDGET_S:g}s query budget), so the "
            f"${scope_total:.2f} {scope} hard-cap total is a lower bound",
        )
    if warnings:
        result.warning = "Arthur circuit breaker: " + "; ".join(warnings)
    return result


# ---------------------------------------------------------------------------
# Breaker state (persisted so every hook invocation shares one verdict)
# ---------------------------------------------------------------------------

STATUS_CLOSED = "closed"
STATUS_OPEN = "open"

# A prompt that starts with "breaker override", "circuit breaker bypass",
# "override the arthur breaker" ... with an optional "for 45m" / "2h" tail.
# Anchored to the start so a prompt that merely talks about the breaker (e.g.
# while editing this file) is not mistaken for an override.
_BREAKER_WORDS = r"(?:arthur\s+)?(?:circuit[\s-]?)?breaker"
OVERRIDE_PATTERN = re.compile(
    rf"^\s*(?:{_BREAKER_WORDS}\s*[:,]?\s*(?:override|bypass)"
    rf"|(?:override|bypass)\s+(?:the\s+)?{_BREAKER_WORDS})\b"
    r"(?:\s+(?:for\s+)?(?P<n>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>m|min|mins|minutes?|h|hr|hrs|hours?)\b)?",
    re.IGNORECASE,
)


def parse_override(prompt: str, config: dict) -> Optional[float]:
    """Minutes the prompt asks the breaker to be lifted for, or None if the
    prompt is not an override command."""
    m = OVERRIDE_PATTERN.match(prompt or "")
    if not m:
        return None
    if m.group("n"):
        minutes = float(m.group("n"))
        if m.group("unit").lower().startswith("h"):
            minutes *= 60
        return minutes
    return float(config.get("override_minutes", DEFAULT_CONFIG["override_minutes"]))


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


def _state_age_s(p: Path, now_ts: float) -> float:
    """Seconds since the file last mattered: its mtime, or for an open breaker
    the end of its cooldown if that is later. An open breaker is not rewritten
    while it waits, and after the cooldown it still holds the half-open probe
    that decides whether to close, so its age runs from the cooldown end."""
    last = p.stat().st_mtime
    if p.suffix == ".json":
        state = _load_json_file(p)
        if state.get("status") == STATUS_OPEN:
            with contextlib.suppress(TypeError, ValueError):
                last = max(last, float(state.get("cooldown_until", 0)))
    return now_ts - last


def _prune_stale_state(exclude: str, now_ts: Optional[float] = None) -> None:
    """Drop state and lock files that have not mattered for STATE_MAX_AGE_S
    (session-scope keys are created per Claude Code session and never
    revisited, so they can only be cleaned up by age)."""
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    try:
        for p in STATE_DIR.iterdir():
            if p.stem == exclude or p.suffix not in (".json", ".lock"):
                continue
            with contextlib.suppress(OSError):
                if _state_age_s(p, now_ts) > STATE_MAX_AGE_S:
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


def _reset_hint(config: dict) -> str:
    minutes = float(config.get("override_minutes", DEFAULT_CONFIG["override_minutes"]))
    return (
        f'send "breaker override" as your next prompt to lift it for {minutes:g} min '
        f'("breaker override for 2h" for longer), '
        f'or reset with: python3 "{Path(__file__).resolve()}" reset'
    )


def decide(
    engine: dict,
    config: dict,
    session_id: str,
    now: Optional[datetime] = None,
    deadline: Optional[Deadline] = None,
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

        # A "breaker override" prompt lifts the breaker for a while; once it
        # lapses the normal closed-state check resumes and may trip again.
        if now_ts < float(state.get("override_until", 0)):
            return Verdict(tripped=False)

        if status == STATUS_OPEN:
            opened_at = float(state.get("opened_at", 0))
            if now_ts - opened_at < cooldown_s:
                return Verdict(
                    tripped=True,
                    message=_open_message(state, config, now_ts),
                )
            # Cooldown elapsed: half-open probe.
            evaluation = evaluate(engine, config, session_id, now, deadline)
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
                    cooldown_until=now_ts + cooldown_s,
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

        evaluation = evaluate(engine, config, session_id, now, deadline)
        if evaluation.tripped:
            state = {
                "status": STATUS_OPEN,
                "opened_at": now_ts,
                "cooldown_until": now_ts + cooldown_s,
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


def override(
    engine: dict,
    config: dict,
    session_id: str,
    minutes: float,
    now: Optional[datetime] = None,
) -> str:
    """Close the breaker for this scope and keep it lifted for `minutes`."""
    now = now or datetime.now(timezone.utc)
    now_ts = now.timestamp()
    key = state_key(engine, config, session_id)
    with _state_lock(key):
        state = load_state(key)
        was_open = state.get("status") == STATUS_OPEN
        state = {
            "status": STATUS_CLOSED,
            "override_until": now_ts + minutes * 60,
            "overridden_at": now_ts,
            "last_check_at": 0,
            "last_evaluation": state.get("last_evaluation"),
        }
        save_state(key, state)
    until = datetime.fromtimestamp(
        state["override_until"],
        tz=timezone.utc,
    ).astimezone()
    return (
        f"Arthur circuit breaker overridden ({config['scope']} scope"
        f"{', was open' if was_open else ''}): lifted for {minutes:g} min, "
        f"until {until.strftime('%H:%M %Z')}; burn-rate checks resume after that."
    )


def _open_message(state: dict, config: dict, now_ts: float) -> str:
    cooldown_s = float(config.get("cooldown_minutes", 15)) * 60
    retry_ts = float(state.get("opened_at", now_ts)) + cooldown_s
    # Local wall-clock time with its zone name, plus the remaining minutes so
    # the message reads the same on a UTC container as on a laptop.
    retry_at = datetime.fromtimestamp(retry_ts, tz=timezone.utc).astimezone()
    remaining_min = max(0, int((retry_ts - now_ts + 59) // 60))
    return (
        f"Arthur circuit breaker OPEN ({config['scope']} scope) — {state.get('reason', '')}. "
        f"Claude Code is paused for another {remaining_min} min "
        f"(until {retry_at.strftime('%H:%M %Z')}, when it re-checks the engine), "
        f"or {_reset_hint(config)}"
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
    if event == "user_prompt_submit":
        minutes = parse_override(data.get("prompt", ""), config)
        if minutes:
            message = override(engine, config, session_id, minutes)
            # The override is a command to the breaker, not a prompt: blocking
            # it keeps Claude from reading it as "carry on" and resuming the
            # work the breaker just stopped.
            return {
                "decision": "block",
                "reason": f"{message} The override prompt was not sent to Claude; "
                "send your next prompt to continue.",
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "suppressOriginalPrompt": True,
                },
            }
    deadline = Deadline()
    verdict = decide(engine, config, session_id, deadline=deadline)
    output = hook_output(event, verdict)
    if event == "session_start":
        notices = [config_problem(config)]
        if not verdict.tripped:
            # A key or engine problem was reported by decide() as fail_mode says.
            with contextlib.suppress(EngineError):
                notices.append(check_engine_clock(engine, config, deadline))
        messages = [(output or {}).get("systemMessage")] + [
            f"Arthur circuit breaker: {n}" for n in notices if n
        ]
        if any(messages):
            output = {"systemMessage": "\n".join(m for m in messages if m)}
    return output


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
    clock = ""
    if not evaluation.engine_error:
        with contextlib.suppress(EngineError):
            clock = check_engine_clock(engine, config, Deadline())
    state = load_state(state_key(engine, config, session_id))
    print(
        json.dumps(
            {
                "scope": config["scope"],
                "budget_usd": budget_usd(config),
                "budget_period_hours": config["budget_period_hours"],
                "api_key": engine["key_name"],
                "engine_timezone": config.get("engine_timezone", "UTC"),
                "breaker_status": state.get("status", STATUS_CLOSED),
                "config_warning": config_problem(config),
                "clock_warning": clock,
                "evaluation": evaluation.to_dict(),
            },
            indent=2,
        ),
    )
    return 0


# cli_check exit codes, which install.sh acts on.
CHECK_OK = 0
CHECK_NOT_CONFIGURED = 1
CHECK_AUTH_FAILED = 2
CHECK_UNREACHABLE = 3


def cli_check() -> int:
    """Verify the breaker can read spend: the key has read access and the
    engine's timestamps read right. Prints what it finds."""
    engine = discover_engine_config()
    if engine is None:
        print(
            "Arthur Engine not configured (no api_key/task_id/endpoint); "
            "the circuit breaker is inactive until it is.",
        )
        return CHECK_NOT_CONFIGURED
    config = load_breaker_config()
    try:
        clock = check_engine_clock(engine, config, Deadline())
    except EngineAuthError as e:
        print(f"Arthur Engine refused the breaker's key: {e}", file=sys.stderr)
        print(READ_KEY_HINT, file=sys.stderr)
        return CHECK_AUTH_FAILED
    except EngineError as e:
        print(f"Could not reach Arthur Engine: {e}", file=sys.stderr)
        return CHECK_UNREACHABLE
    print(
        f"OK: {engine['key_name']} can read task {engine['task_id']}'s spans "
        f"at {engine['base_url']}.",
    )
    for warning in (config_problem(config), clock):
        if warning:
            print(f"WARNING: {warning}", file=sys.stderr)
    return CHECK_OK


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: claude_code_circuit_breaker.py "
            "<user_prompt_submit|pre_tool|session_start|status|check|reset>",
            file=sys.stderr,
        )
        sys.exit(0)

    command = sys.argv[1]
    if command == "reset":
        print(f"Cleared {clear_state()} breaker state file(s); breaker is closed.")
        sys.exit(0)
    if command == "status":
        sys.exit(cli_status(sys.argv[2:]))
    if command == "check":
        sys.exit(cli_check())

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
