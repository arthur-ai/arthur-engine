#!/usr/bin/env python3
"""A time-ordered stream where one 3-span block recurs, then the world changes.

The recurring block is the press release's "eleven steps, two doing real work":

    LLM(decide which tool)  ->  TOOL(lookup_order)  ->  LLM(render the reply)

Only the middle span is real work. The two LLM calls are deterministic dispatch
and template rendering, so the block compiles to code wrapped around a
preserved side-effecting call.

The stream runs in three phases so the shadow harness has something to catch:

  baseline      day 1-10   the block behaves as learned
  input_drift   day 11-15  a new intake channel sends inputs the guard has
                           never seen — coverage collapses, quality does not
  output_drift  day 16-20  inputs still look familiar but someone changed the
                           reply format upstream, so the compiled template is
                           now silently wrong. The guard cannot see this; only
                           continued sampling can.
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import synth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 777001
RNG = random.Random(SEED)
IDS = synth.IdGen(SEED)
DAY0 = datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc)

STATUS = ["in_transit", "out_for_delivery", "delivered", "delayed"]
ETA = ["Thursday", "Friday", "Monday", "Sep 14"]
DISPATCH_SYS = "Decide which tool to call and with what arguments."
RENDER_SYS = "Write the customer-facing status line."
OTHER_SYS = "Classify the customer's tone for routing."

# phase 1/2 inputs carry an explicit order number; phase 2 adds a channel that
# refers to orders by a different scheme the guard has never seen
CLASSIC = ["where is my order #{o}", "status of order #{o} please",
           "any update on #{o}", "tracking for order #{o}"]
NEW_CHANNEL = ["checking on my recent purchase from the app",
               "what's happening with the thing i bought yesterday",
               "my latest order — where is it"]


def render(order, status, eta, phase):
    """The recorded reply format. It changes in the output_drift phase."""
    if phase == "output_drift":
        return (f"Order {order}: {status.replace('_', ' ')}. Estimated {eta}. "
                f"Tracking code TRK{order}.")
    return f"Order {order} is {status.replace('_', ' ')} and arrives {eta}."


def block_trace(day, phase):
    order = str(RNG.randint(1000, 99999))
    status, eta = RNG.choice(STATUS), RNG.choice(ETA)
    if phase == "input_drift" and RNG.random() < 0.55:
        user = RNG.choice(NEW_CHANNEL)
        looks_familiar = False
    else:
        user = RNG.choice(CLASSIC).format(o=order)
        looks_familiar = True
    final = render(order, status, eta, phase)

    trace_id = IDS.trace()
    root_id = IDS.span()
    t = DAY0 + timedelta(days=day, seconds=RNG.randint(0, 80000))
    spans = []

    def add(name, kind, attrs, ms):
        nonlocal t
        s = synth.make_span(trace_id=trace_id, span_id=IDS.span(), parent_span_id=root_id,
                            name=name, kind=kind, start=t, duration_ms=ms,
                            flat_attrs=attrs, session_id=f"sess_{day:02d}")
        t += timedelta(milliseconds=ms + 5)
        spans.append(s)
        return s

    add("ChatCompletion", "LLM", synth.llm_attrs(
        model="gpt-4o", system=DISPATCH_SYS, user=user, output="",
        prompt_tokens=RNG.randint(400, 520), completion_tokens=RNG.randint(20, 30),
        temperature=0.0, node_id="block.dispatch",
        tool_calls=[{"id": "call_" + IDS.hex(4), "name": "lookup_order",
                     "args": {"order_id": order}}]), RNG.uniform(760, 1180))
    add("lookup_order", "TOOL", synth.tool_attrs(
        name="lookup_order", args={"order_id": order},
        result={"order_id": order, "status": status, "eta": eta}), RNG.uniform(150, 260))
    add("ChatCompletion", "LLM", synth.llm_attrs(
        model="gpt-4o", system=RENDER_SYS, user=json.dumps(
            {"order_id": order, "status": status, "eta": eta}),
        output=final, prompt_tokens=RNG.randint(430, 560),
        completion_tokens=RNG.randint(24, 40), temperature=0.2,
        node_id="block.render"), RNG.uniform(820, 1320))
    # a fourth call that is genuinely loose, so the miner has to ignore it
    if RNG.random() < 0.45:
        add("ChatCompletion", "LLM", synth.llm_attrs(
            model="gpt-4o", system=OTHER_SYS, user=user,
            output=RNG.choice(["calm and factual", "mildly annoyed", "polite but firm",
                               "frustrated", "neutral enquiry"]),
            prompt_tokens=RNG.randint(380, 460), completion_tokens=RNG.randint(6, 14),
            temperature=0.8, node_id="tone.classify"), RNG.uniform(600, 900))

    root = synth.make_span(
        trace_id=trace_id, span_id=root_id, name="order-status-agent.run", kind="AGENT",
        start=DAY0 + timedelta(days=day, seconds=RNG.randint(0, 80000)),
        duration_ms=sum((int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1e6
                        for s in spans) + 40,
        flat_attrs=synth.root_attrs(question=user, answer=final,
                                    agent="order-status-agent",
                                    metadata={"phase": phase, "day": day,
                                              "looks_familiar": looks_familiar}),
        session_id=f"sess_{day:02d}")
    return {"trace_id": trace_id, "root_span_id": root_id, "spans": [root] + spans,
            "_phase": phase, "_day": day}


PHASES = [("baseline", range(0, 10), 26), ("input_drift", range(10, 15), 26),
          ("output_drift", range(15, 20), 26)]


def main():
    traces = []
    for phase, days, per_day in PHASES:
        for day in days:
            for _ in range(per_day):
                traces.append(block_trace(day, phase))
    traces.sort(key=lambda t: int(t["spans"][1]["startTimeUnixNano"]))

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", "stream.json"), "w") as fh:
        json.dump(traces, fh, separators=(",", ":"))
        fh.write("\n")
    with open(os.path.join(HERE, "out", "stream.meta.json"), "w") as fh:
        json.dump({"seed": SEED, "traces": len(traces),
                   "phases": {p: [min(d), max(d)] for p, d, _ in PHASES},
                   "expected": {
                       "input_drift": "guard coverage should fall; agreement inside the "
                                      "guard should hold",
                       "output_drift": "guard coverage should hold; sampled agreement "
                                       "should fall — only sampling can see this"}},
                  fh, indent=1)
        fh.write("\n")
    print(f"{len(traces)} traces over 20 days -> out/stream.json")
    for phase, days, _ in PHASES:
        n = sum(1 for t in traces if t["_phase"] == phase)
        print(f"  {phase:<14} days {min(days):>2}-{max(days):<2}  {n:>4} traces")


if __name__ == "__main__":
    main()
