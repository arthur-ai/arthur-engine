#!/usr/bin/env python3
"""Spend circuit breaker for Codex CLI (stdlib only).

Codex hooks cannot end a turn mid-way: `continue: false` on PreToolUse makes
Codex reject the whole reply and run the tool. So the breaker does the two
things Codex honours:
  UserPromptSubmit -> {"decision": "block"} while over the cap (and handles
                      "breaker status|override|reset" without the model)
  PreToolUse       -> permissionDecision "deny" with a reason telling the model
                      to stop
Spend is priced locally from the rollout's per-response usage records, so it is
current after every model response, with no engine call.

Usage in hooks.json: python3 codex_spend_breaker.py   (event read from stdin)
Config (env): ARTHUR_BREAKER_CAP_USD    USD per 5-minute window (default 0.10)
              ARTHUR_BREAKER_STATE      state file (default $CODEX_HOME/spend_breaker_state.json)
              ARTHUR_BREAKER_MODEL      price row when the rollout names no model
              ARTHUR_BREAKER_RATES_JSON extra or replacement price rows, as
                                        {"model": {"input": .., "cached": .., "output": ..}}
              ARTHUR_BREAKER_LOG        append one line per hook call to this file

Any error lets Codex carry on: the hook prints nothing and exits 0.
"""

import fcntl
import json
import math
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime

WINDOW_S = 5 * 60
OVERRIDE_S = 10 * 60
SESSION_TTL_S = 24 * 3600  # forget a session's read position after a day idle
COMMAND = re.compile(r"^\s*breaker\s+(status|override|reset)\s*$", re.I)

# USD per million tokens. Unknown models are priced at the most expensive row
# rather than at zero; ARTHUR_BREAKER_RATES_JSON adds or replaces rows.
RATES = {
    "gpt-6-astra": {"input": 10.0, "cached": 1.0, "output": 50.0},
    "gpt-5.6-sol": {"input": 4.0, "cached": 0.9256, "output": 20.0},
}
FALLBACK = "gpt-6-astra"


def cap():
    return float(os.environ.get("ARTHUR_BREAKER_CAP_USD", "0.10"))


def state_path():
    default = os.path.join(os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex")), "spend_breaker_state.json")
    return os.environ.get("ARTHUR_BREAKER_STATE", default)


def load_state():
    try:
        with open(state_path()) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    state.setdefault("spend", {})
    state.setdefault("override_until", 0)
    state.setdefault("reset_at", 0)
    state.setdefault("sessions", {})
    return state


def save_state(state):
    # A temporary file of its own per write, then an atomic replace.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(state_path()) or ".", prefix=".spend_breaker.")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f)
    os.replace(tmp, state_path())


@contextmanager
def locked():
    """Every Codex session's hooks share one state file: hold an exclusive lock
    from load to save so concurrent hooks can't overwrite each other's spend."""
    with open(state_path() + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def rates():
    """The built-in price rows plus ARTHUR_BREAKER_RATES_JSON. A row is used only
    when it is an object with a finite, non-negative number for each of input,
    cached and output (JSON here accepts Infinity and NaN); any
    other value is ignored, so a bad row can't make every hook fail (and the
    breaker silently stop)."""
    table = dict(RATES)
    try:
        extra = json.loads(os.environ.get("ARTHUR_BREAKER_RATES_JSON") or "{}")
    except ValueError:
        return table
    if not isinstance(extra, dict):
        return table
    for model, row in extra.items():
        rate = _rate_row(row)
        if rate:
            table[model] = rate
    return table


def _rate_row(row):
    """{input, cached, output} as floats, or None unless each is a finite,
    non-negative number (an integer too large for a float counts as invalid)."""
    if not isinstance(row, dict):
        return None
    rate = {}
    for k in ("input", "cached", "output"):
        v = row.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        try:
            v = float(v)
        except OverflowError:
            return None
        if not math.isfinite(v) or v < 0:
            return None
        rate[k] = v
    return rate


def price(model, usage):
    table = rates()
    # An unknown model gets the highest rate of each kind, not one row's rates.
    r = table.get(model) or {k: max(row[k] for row in table.values()) for k in ("input", "cached", "output")}
    cached = usage.get("cached_input_tokens", 0)
    uncached = max(usage.get("input_tokens", 0) - cached, 0)
    out = usage.get("output_tokens", 0)  # includes reasoning tokens
    return (uncached * r["input"] + cached * r["cached"] + out * r["output"]) / 1e6


def ingest(state, transcript_path, session_id):
    """Add the rollout's new model responses to the spend ledger.

    Each session's rollout is read from where the last hook stopped, so a hook
    costs the same however long the session is. `token_usage_record` lands as
    each response finishes, before its tool runs, keyed by response id. Older
    rollouts only have `token_count`, which lands after the tool and can repeat
    the last response's usage (for a rate-limit update), so one counts only when
    the cumulative total moves. Responses from before a `breaker reset` are
    skipped.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return
    sess = state["sessions"].get(session_id) or {}
    if sess.get("path") != transcript_path or sess.get("pos", 0) > os.path.getsize(transcript_path):
        sess = {"path": transcript_path, "pos": 0}
    model = sess.get("model") or os.environ.get("ARTHUR_BREAKER_MODEL", FALLBACK)
    last_total = sess.get("last_total", 0)
    with open(transcript_path, "rb") as f:
        f.seek(sess.get("pos", 0))
        for raw in f:
            if not raw.endswith(b"\n"):
                break  # a line Codex is still writing: read it next time
            sess["pos"] = sess.get("pos", 0) + len(raw)
            try:
                e = json.loads(raw)
            except ValueError:
                continue
            p = e.get("payload") or {}
            if e.get("type") == "turn_context" and p.get("model"):
                model = p["model"]
            usage, key = None, None
            if e.get("type") == "token_usage_record" and p.get("usage"):
                usage, key = p["usage"], f"{session_id}:{p.get('response_id') or sess['pos']}"
                sess["has_records"] = True
            elif p.get("type") == "token_count" and p.get("info") and not sess.get("has_records"):
                total = (p["info"].get("total_token_usage") or {}).get("total_tokens", 0)
                if total > last_total:
                    last_total = total
                    usage, key = p["info"].get("last_token_usage") or {}, f"{session_id}:pos{sess['pos']}"
            if not usage or key in state["spend"]:
                continue
            ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp()
            if ts <= state.get("reset_at", 0):
                continue
            state["spend"][key] = [ts, price(model, usage), model]
    sess.update(model=model, last_total=last_total, seen=time.time())
    state["sessions"][session_id] = sess


def window_spend(state, now):
    return sum(usd for ts, usd, *_ in state["spend"].values() if now - ts <= WINDOW_S)


def main():
    event = json.load(sys.stdin)
    with locked():
        return decide(event)


def decide(event):
    name = event.get("hook_event_name")
    now = time.time()
    state = load_state()
    ingest(state, event.get("transcript_path"), event.get("session_id", "?"))
    # Keep the state small: spend outside the window can't matter again.
    state["spend"] = {k: v for k, v in state["spend"].items() if now - v[0] <= WINDOW_S}
    state["sessions"] = {k: v for k, v in state["sessions"].items() if now - v.get("seen", now) <= SESSION_TTL_S}
    spent = window_spend(state, now)
    overridden = state.get("override_until", 0) > now
    tripped = spent >= cap() and not overridden
    reply = {}

    if name == "UserPromptSubmit":
        m = COMMAND.match(event.get("prompt") or "")
        if m:
            verb = m.group(1).lower()
            if verb == "override":
                state["override_until"] = now + OVERRIDE_S
            if verb == "reset":
                # Responses already in the rollouts must not come back on the next hook.
                state["spend"], state["override_until"], state["reset_at"] = {}, 0, now
                spent = 0.0
            until = state.get("override_until", 0)
            lifted = f"; lifted until {time.strftime('%H:%M:%S', time.localtime(until))}" if until > now else ""
            tripped = False
            reply = {"decision": "block", "reason": f"Arthur spend breaker {verb}: ${spent:.4f} in the last 5 min (cap ${cap()}){lifted}."}
        elif tripped:
            reply = {"decision": "block", "reason": f"Arthur spend breaker: ${spent:.4f} spent in the last 5 min (cap ${cap()}). Paused. Type \"breaker override\" to lift it for 10 min."}
    elif name == "PreToolUse" and tripped:
        reply = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Arthur spend breaker: ${spent:.4f} spent in the last 5 min (cap ${cap()}). Spending is paused: do not call any more tools, stop now and tell the user the spend breaker paused the session.",
            }
        }

    save_state(state)
    log_path = os.environ.get("ARTHUR_BREAKER_LOG")
    if log_path:
        why = reply.get("reason") or reply.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        with open(log_path, "a") as log:
            log.write(f"{time.strftime('%H:%M:%S')} {name} spent=${spent:.4f} cap=${cap()} tripped={tripped}" + (f" -> {why[:110]}" if why else "") + "\n")
    return reply


if __name__ == "__main__":
    try:
        out = main()
    except Exception:  # never fail a Codex prompt or tool call because of the breaker
        out = {}
    if out:
        print(json.dumps(out))
