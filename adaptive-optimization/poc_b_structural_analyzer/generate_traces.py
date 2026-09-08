#!/usr/bin/env python3
"""Traces carrying planted structural anti-patterns, plus clean controls.

Structure is observable in a single trace; distribution is not. These are the
findings that need no corpus, no eval, and no statistics — which also makes
them the only ones available on day one for an agent with no history.

Planted patterns (ground truth in traces.meta.json):
  dead_llm_call        an LLM call whose output nothing downstream reads
  verbatim_dispatch    tool-call arguments copied straight out of the input
  passthrough_reformat an LLM call that restates the preceding tool result
  redundant_call       the same call site invoked twice on identical input
  rebuilt_prefix       a large context re-sent on every call in the trace
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import synth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 90210
RNG = random.Random(SEED)
IDS = synth.IdGen(SEED)
T0 = datetime(2026, 9, 2, 9, 0, 0, tzinfo=timezone.utc)

BIG_CONTEXT = (
    "COMPANY POLICY DIGEST v14. Refunds: orders delayed beyond five business days "
    "qualify for a full refund to the original payment method within ten business "
    "days. Warranty: electronics carry a twelve month limited warranty against "
    "manufacturing defects; accidental damage is excluded. Shipping: standard "
    "delivery is three to five business days domestically. Escalation: tier one "
    "agents may issue credits up to one hundred dollars without approval. "
) * 3

ORDERS = ["7781", "6120", "9034", "5567", "4412", "8890"]
CITIES = ["Springfield", "Ashford", "Bellport", "Cranwell"]


class TraceBuilder:
    def __init__(self, question: str, answer: str):
        self.trace_id = IDS.trace()
        self.root_id = IDS.span()
        self.cursor = T0 + timedelta(seconds=RNG.randint(0, 80000))
        self.spans: list[dict] = []
        self.question = question
        self.answer = answer

    def add(self, *, name, kind, flat_attrs, ms, parent=None):
        span = synth.make_span(
            trace_id=self.trace_id, span_id=IDS.span(),
            parent_span_id=parent or self.root_id, name=name, kind=kind,
            start=self.cursor, duration_ms=ms, flat_attrs=flat_attrs,
            session_id="sess_struct", user_id="user-7")
        self.cursor += timedelta(milliseconds=ms + 5)
        self.spans.append(span)
        return span

    def finish(self):
        total = (self.cursor - (T0 + timedelta(seconds=0))).total_seconds()
        root = synth.make_span(
            trace_id=self.trace_id, span_id=self.root_id, name="support-agent.run",
            kind="AGENT", start=self.spans[0]["startTimeUnixNano"] and
            datetime.fromtimestamp(int(self.spans[0]["startTimeUnixNano"]) / 1e9,
                                   tz=timezone.utc) - timedelta(milliseconds=15),
            duration_ms=sum(
                (int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1e6
                for s in self.spans) + 40,
            flat_attrs=synth.root_attrs(question=self.question, answer=self.answer,
                                        agent="support-agent"),
            session_id="sess_struct", user_id="user-7")
        return {"trace_id": self.trace_id, "root_span_id": self.root_id,
                "spans": [root] + self.spans}


def clean_trace():
    """Every call's output is consumed; dispatch args are derived, not copied."""
    order = RNG.choice(ORDERS)
    q = f"my order placed last tuesday hasn't arrived, can you check it"
    ans = f"Order #{order} is in transit and arrives Thursday."
    b = TraceBuilder(q, ans)
    # the model resolves "last tuesday" into a date — a derived argument, so the
    # dispatch is real work and must not be flagged
    b.add(name="ChatCompletion", kind="LLM", ms=900,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Decide which tool to call.", user=q,
              output="", prompt_tokens=420, completion_tokens=28, temperature=0.0,
              node_id="agent.dispatch",
              tool_calls=[{"id": "call_" + IDS.hex(4), "name": "find_order_by_date",
                           "args": {"placed_on": "2026-08-26", "customer": "user-7"}}]))
    b.add(name="find_order_by_date", kind="TOOL", ms=210,
          flat_attrs=synth.tool_attrs(
              name="find_order_by_date", args={"placed_on": "2026-08-26"},
              result={"order_id": order, "status": "in_transit", "eta": "Thursday"}))
    b.add(name="ChatCompletion", kind="LLM", ms=1100,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Write the customer reply.",
              user=f"order {order} status in_transit eta Thursday",
              output=ans, prompt_tokens=510, completion_tokens=42, temperature=0.3,
              node_id="agent.reply"))
    return b.finish(), []


def dead_call_trace():
    """A sentiment score is computed, logged nowhere, and read by nothing."""
    order = RNG.choice(ORDERS)
    q = f"where is order #{order}"
    ans = f"Order #{order} is out for delivery."
    b = TraceBuilder(q, ans)
    b.add(name="ChatCompletion", kind="LLM", ms=640,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Score the emotional intensity of this message 1-10.",
              user=q, output="intensity 7 of 10 with mild frustration detected",
              prompt_tokens=380, completion_tokens=22, temperature=0.4,
              node_id="agent.emotion_probe"))
    b.add(name="lookup_order", kind="TOOL", ms=180,
          flat_attrs=synth.tool_attrs(name="lookup_order", args={"order_id": order},
                                      result={"status": "out_for_delivery"}))
    b.add(name="ChatCompletion", kind="LLM", ms=980,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Write the customer reply.",
              user=f"order {order} status out_for_delivery", output=ans,
              prompt_tokens=460, completion_tokens=30, temperature=0.3,
              node_id="agent.reply"))
    return b.finish(), ["dead_llm_call"]


def verbatim_dispatch_trace():
    """The model is asked to pick a tool and copies the order id out of the text."""
    order = RNG.choice(ORDERS)
    q = f"i was charged twice for order #{order}, please refund"
    ans = f"A duplicate charge on #{order} was refunded."
    b = TraceBuilder(q, ans)
    b.add(name="ChatCompletion", kind="LLM", ms=870,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Decide which tool to call.", user=q, output="",
              prompt_tokens=430, completion_tokens=26, temperature=0.0,
              node_id="agent.dispatch",
              tool_calls=[{"id": "call_" + IDS.hex(4), "name": "lookup_charges",
                           "args": {"order_id": order}}]))
    b.add(name="lookup_charges", kind="TOOL", ms=230,
          flat_attrs=synth.tool_attrs(name="lookup_charges", args={"order_id": order},
                                      result={"duplicate": True, "amount": 84.0}))
    b.add(name="ChatCompletion", kind="LLM", ms=1020,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Write the customer reply.",
              user=f"duplicate charge on {order} amount 84.0", output=ans,
              prompt_tokens=470, completion_tokens=34, temperature=0.3,
              node_id="agent.reply"))
    return b.finish(), ["verbatim_dispatch"]


def passthrough_trace():
    """A model call that reformats a tool result and adds nothing."""
    order = RNG.choice(ORDERS)
    city = RNG.choice(CITIES)
    q = f"tracking for #{order}"
    result = {"order_id": order, "status": "in_transit", "city": city, "eta": "Thursday"}
    restated = (f"order {order} status in_transit city {city} eta Thursday")
    b = TraceBuilder(q, restated)
    b.add(name="track_order", kind="TOOL", ms=190,
          flat_attrs=synth.tool_attrs(name="track_order", args={"order_id": order},
                                      result=result))
    b.add(name="ChatCompletion", kind="LLM", ms=760,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Restate the tool output as a sentence.",
              user=json.dumps(result), output=restated,
              prompt_tokens=400, completion_tokens=26, temperature=0.2,
              node_id="agent.format_result"))
    return b.finish(), ["passthrough_reformat"]


def redundant_trace():
    """The same classification is run twice on identical input inside one trace."""
    q = "the api is completely down and nobody can log in"
    ans = "Escalated as P1."
    b = TraceBuilder(q, ans)
    for _ in range(2):
        b.add(name="ChatCompletion", kind="LLM", ms=820,
              flat_attrs=synth.llm_attrs(
                  model="gpt-4o", system="Classify the urgency as P1, P2 or P3.",
                  user=q, output="p1", prompt_tokens=390, completion_tokens=3,
                  temperature=0.0, node_id="triage.urgency"))
    b.add(name="create_incident", kind="TOOL", ms=240,
          flat_attrs=synth.tool_attrs(name="create_incident", args={"severity": "p1"},
                                      result={"incident": "INC-3391"}))
    b.add(name="ChatCompletion", kind="LLM", ms=900,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Write the customer reply.",
              user="p1 incident INC-3391", output=ans, prompt_tokens=440,
              completion_tokens=18, temperature=0.3, node_id="agent.reply"))
    return b.finish(), ["redundant_call"]


def rebuilt_prefix_trace():
    """A 1.5KB policy digest re-sent verbatim on all three calls in the trace."""
    order = RNG.choice(ORDERS)
    q = f"is my late order #{order} refundable"
    ans = "Yes — delays beyond five business days qualify for a full refund."
    b = TraceBuilder(q, ans)
    for node, sysp, out, ctok in (
        ("policy.classify", "Classify the policy area.", "refunds", 4),
        ("policy.check", "Decide whether the policy applies.", "applies", 5),
        ("policy.explain", "Explain the outcome to the customer.", ans, 30),
    ):
        b.add(name="ChatCompletion", kind="LLM", ms=1080,
              flat_attrs=synth.llm_attrs(
                  model="gpt-4o", system=BIG_CONTEXT + "\n" + sysp,
                  user=q, output=out, prompt_tokens=1180, completion_tokens=ctok,
                  temperature=0.0, node_id=node))
    return b.finish(), ["rebuilt_prefix"]


def near_miss_answer_only():
    """The LLM's value is read by nothing except the final answer.

    A naive dead-call detector flags this. It must not: the trace answer is a
    consumer, and this call is the only thing producing the figure in it.
    """
    order = RNG.choice(ORDERS)
    q = f"how much was i refunded on #{order}"
    amount = f"{RNG.randint(20, 300)}.00"
    ans = f"You were refunded ${amount} on order #{order}."
    b = TraceBuilder(q, ans)
    b.add(name="ChatCompletion", kind="LLM", ms=700,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Compute the refunded amount from the ledger rows.",
              user=f"rows: charge {amount} reversal {amount} order {order}",
              output=f"refunded {amount} on order {order}",
              prompt_tokens=410, completion_tokens=20, temperature=0.0,
              node_id="ledger.compute"))
    return b.finish(), []


def near_miss_partial_args():
    """One tool argument is copied, the other is genuinely derived.

    Substituting a script here would silently drop the derivation, so a
    detector that fires on *any* verbatim argument is wrong.
    """
    order = RNG.choice(ORDERS)
    q = f"refund order #{order} that i placed last tuesday"
    ans = f"Refund issued on #{order}."
    b = TraceBuilder(q, ans)
    b.add(name="ChatCompletion", kind="LLM", ms=910,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Decide which tool to call.", user=q, output="",
              prompt_tokens=440, completion_tokens=30, temperature=0.0,
              node_id="agent.dispatch",
              tool_calls=[{"id": "call_" + IDS.hex(4), "name": "issue_refund",
                           "args": {"order_id": order, "placed_on": "2026-08-26"}}]))
    b.add(name="issue_refund", kind="TOOL", ms=320,
          flat_attrs=synth.tool_attrs(name="issue_refund",
                                      args={"order_id": order, "placed_on": "2026-08-26"},
                                      result={"refund_id": "RF-" + IDS.hex(2)}))
    b.add(name="ChatCompletion", kind="LLM", ms=880,
          flat_attrs=synth.llm_attrs(
              model="gpt-4o", system="Write the customer reply.",
              user=f"refund issued for {order} confirmation pending mailer",
              output=ans, prompt_tokens=450, completion_tokens=22, temperature=0.3,
              node_id="agent.reply"))
    return b.finish(), []


PLAN = [(clean_trace, 60), (near_miss_answer_only, 25), (near_miss_partial_args, 25), (dead_call_trace, 40), (verbatim_dispatch_trace, 40),
        (passthrough_trace, 40), (redundant_trace, 30), (rebuilt_prefix_trace, 30)]


def main():
    traces, truth = [], {}
    for factory, count in PLAN:
        for _ in range(count):
            trace, findings = factory()
            traces.append(trace)
            truth[trace["trace_id"]] = findings
    RNG.shuffle(traces)

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", "traces.json"), "w") as fh:
        json.dump(traces, fh, separators=(",", ":"))
        fh.write("\n")
    with open(os.path.join(HERE, "out", "traces.meta.json"), "w") as fh:
        json.dump({"seed": SEED, "traces": len(traces), "ground_truth": truth,
                   "patterns": sorted({f for v in truth.values() for f in v})},
                  fh, indent=1)
        fh.write("\n")
    n_clean = sum(1 for v in truth.values() if not v)
    print(f"{len(traces)} traces ({n_clean} clean controls, "
          f"{len(traces) - n_clean} with a planted pattern) -> out/traces.json")
    for pat in sorted({f for v in truth.values() for f in v}):
        print(f"  {pat:<22}{sum(1 for v in truth.values() if pat in v):>5}")


if __name__ == "__main__":
    main()
