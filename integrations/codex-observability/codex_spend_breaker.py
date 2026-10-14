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

import json
import os
import re
import sys
import time
from datetime import datetime

WINDOW_S = 5 * 60
OVERRIDE_S = 10 * 60
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
            return json.load(f)
    except (OSError, ValueError):
        return {"spend": {}, "override_until": 0}


def save_state(state):
    tmp = state_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, state_path())


def rates():
    table = dict(RATES)
    try:
        table.update(json.loads(os.environ.get("ARTHUR_BREAKER_RATES_JSON") or "{}"))
    except ValueError:
        pass
    return table


def price(model, usage):
    table = rates()
    r = table.get(model) or max(table.values(), key=lambda row: row["output"])
    cached = usage.get("cached_input_tokens", 0)
    uncached = max(usage.get("input_tokens", 0) - cached, 0)
    out = usage.get("output_tokens", 0)  # includes reasoning tokens
    return (uncached * r["input"] + cached * r["cached"] + out * r["output"]) / 1e6


def ingest(state, transcript_path, session_id):
    """Add every model response in the rollout to the spend ledger (idempotent).

    `token_usage_record` lands as each response finishes, before its tool runs,
    keyed by response id; older rollouts only have `token_count`, which lands
    after the tool, so it is the fallback.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return
    model = os.environ.get("ARTHUR_BREAKER_MODEL", FALLBACK)
    records, counts = {}, {}
    with open(transcript_path, errors="replace") as f:
        for n, line in enumerate(f):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            p = e.get("payload") or {}
            if e.get("type") == "turn_context" and p.get("model"):
                model = p["model"]
            ts = e.get("timestamp")
            if e.get("type") == "token_usage_record" and p.get("usage"):
                records[f"{session_id}:{p.get('response_id') or n}"] = (ts, p["usage"], model)
            elif p.get("type") == "token_count" and p.get("info"):
                last = p["info"].get("last_token_usage") or {}
                if last.get("total_tokens"):
                    counts[f"{session_id}:line{n}"] = (ts, last, model)
    for key, (ts, usage, m) in (records or counts).items():
        if key not in state["spend"]:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            state["spend"][key] = [t, price(m, usage), m]


def window_spend(state, now):
    return sum(usd for ts, usd, *_ in state["spend"].values() if now - ts <= WINDOW_S)


def main():
    event = json.load(sys.stdin)
    name = event.get("hook_event_name")
    now = time.time()
    state = load_state()
    ingest(state, event.get("transcript_path"), event.get("session_id", "?"))
    # Keep the ledger small: entries outside the window can't matter again.
    state["spend"] = {k: v for k, v in state["spend"].items() if now - v[0] <= WINDOW_S}
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
                state["spend"], state["override_until"] = {}, 0
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
