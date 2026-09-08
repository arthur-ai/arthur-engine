#!/usr/bin/env python3
"""Synthetic production corpus for one agent, shaped for tightness analysis.

Seven call sites spanning the whole spectrum, with ground truth recorded in
corpus.meta.json so the POC can be scored on precision rather than eyeballed:

  triage.urgency    TIGHT       keyword-driven 3-way label, temperature 1.0 set
                                by accident (the free "set it to 0" finding)
  route.team        PARTIAL     tight for ~85% of traffic, loose in the tail
  lang.detect       TIGHT       stopword-driven, no temperature ever passed
  extract.order_id  TIGHT       output is a verbatim substring of the input
  summarize.thread  LOOSE       open-ended text, must be rejected
  draft.reply       LOOSE       open-ended text on the most expensive model —
                                the top cost centre must still be rejected
  sentiment.gate    DEGENERATE  always returns "neutral"; a dead call wearing a
                                model's clothes

Also emits a `resamples` fixture: the same recorded inputs run through the same
model three times. In production that is a real (cheap) re-run; here it is
synthesized, and it is what separates a loose function from a tight one being
sampled noisily.
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import synth  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 424242
RNG = random.Random(SEED)
IDS = synth.IdGen(SEED)
T0 = datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc)

# ── vocabulary banks ──────────────────────────────────────────────────────────

P1 = ["the checkout api is completely down", "total outage across all regions",
      "we suspect a security breach in our account", "nobody can access the dashboard",
      "production is hard down since 04:00", "data loss suspected after the failed migration"]
P2 = ["responses are extremely slow this morning", "intermittent 500 error on report export",
      "search results are degraded for some users", "webhooks are lagging by twenty minutes",
      "the export job keeps timing out"]
P3 = ["how do i change my billing email", "can you send last month invoice again",
      "question about seat pricing for next year", "where do i find the audit log",
      "please update our company address", "is there a dark mode setting"]

TEAM = {
    "billing":    ["invoice", "refund", "vat", "receipt", "chargeback", "proration"],
    "platform":   ["latency", "timeout", "throughput", "deploy", "cluster", "quota"],
    "security":   ["breach", "phishing", "mfa", "pentest", "credential", "soc2"],
    "onboarding": ["provisioning", "sso setup", "sandbox", "kickoff", "migration plan", "trial"],
}
TEAM_AMBIGUOUS = ["this is not working properly", "please look into our account",
                  "something seems off since yesterday", "following up on my last message",
                  "need help with the thing we discussed", "any update on this"]

LANG = {
    "en": ["the invoice is wrong and i need a corrected copy",
           "i cannot log in to my account this morning"],
    "es": ["la factura esta incorrecta y necesito una copia corregida",
           "no puedo acceder a mi cuenta esta manana"],
    "de": ["die rechnung ist falsch und ich brauche eine korrigierte kopie",
           "ich kann mich heute morgen nicht anmelden"],
    "fr": ["la facture est incorrecte et je voudrais une copie corrigee",
           "je ne peux pas me connecter a mon compte ce matin"],
    "pt": ["a fatura esta incorreta e preciso de uma copia corrigida",
           "nao consigo entrar na minha conta esta manha"],
}

SUM_OPEN = ["Customer reports", "Thread covers", "User describes", "Ticket concerns",
            "Conversation is about", "Summary:"]
SUM_MID = ["a billing discrepancy", "repeated login failures", "slow export performance",
           "a request to change account details", "confusion about seat pricing",
           "an unexpected charge", "missing webhook deliveries"]
SUM_TAIL = ["and asks for a callback.", "with two follow-ups unanswered.",
            "escalated once already.", "and appears resolved.",
            "pending a fix from engineering.", "with no clear next step."]

REPLY_OPEN = ["Thanks for reaching out", "Apologies for the trouble", "Happy to help here",
              "Thanks for your patience", "Sorry about the confusion"]
REPLY_MID = ["I've checked your account and", "Looking at the logs,", "After reviewing this,",
             "I can confirm that", "It looks like"]
REPLY_TAIL = ["the charge will be reversed within five business days.",
              "our engineers are deploying a fix this afternoon.",
              "I've updated the setting on your behalf.",
              "I've escalated this to the platform team.",
              "you should see this resolved shortly."]


def p1_p2_p3():
    r = RNG.random()
    if r < 0.18:
        return RNG.choice(P1), "p1"
    if r < 0.52:
        return RNG.choice(P2), "p2"
    return RNG.choice(P3), "p3"


# ── call-site definitions ─────────────────────────────────────────────────────
# Each returns (user_text, model_output). `noise` is applied by the driver.

def cs_triage():
    text, label = p1_p2_p3()
    text = f"[ticket] {text}"
    return text, label


def cs_route():
    if RNG.random() < 0.85:
        team = RNG.choice(list(TEAM))
        kw = RNG.choice(TEAM[team])
        return f"subject: {kw} issue — {RNG.choice(['urgent', 'please advise', 'follow up'])}", team
    # ambiguous tail: deliberately vocabulary-free, and the label really is arbitrary
    return RNG.choice(TEAM_AMBIGUOUS), RNG.choice(list(TEAM))


def cs_lang():
    code = RNG.choice(list(LANG))
    return RNG.choice(LANG[code]), code


def cs_extract():
    oid = str(RNG.randint(1000, 99999))
    tmpl = RNG.choice([
        "where is my order #{o}? it was due last week",
        "order #{o} arrived damaged, please advise",
        "can you check the status of #{o} for me",
        "i was charged twice for order #{o}",
    ])
    return tmpl.format(o=oid), oid


def cs_summarize():
    body = " ".join([RNG.choice(SUM_MID), RNG.choice(SUM_TAIL),
                     RNG.choice(SUM_MID), RNG.choice(SUM_TAIL)])
    text = f"[thread of {RNG.randint(3, 9)} messages] {body}"
    out = f"{RNG.choice(SUM_OPEN)} {RNG.choice(SUM_MID)} {RNG.choice(SUM_TAIL)}"
    return text, out


def cs_draft():
    text = f"[draft a reply] customer says: {RNG.choice(P1 + P2 + P3)}"
    out = f"{RNG.choice(REPLY_OPEN)} — {RNG.choice(REPLY_MID)} {RNG.choice(REPLY_TAIL)}"
    return text, out


def cs_sentiment():
    text = f"[gate] {RNG.choice(P1 + P2 + P3)}"
    return text, "neutral"   # broken prompt: label never varies


CALL_SITES = [
    # name, system prompt, model, temperature, gen, noise, prompt_tok, comp_tok, ms, weight
    ("triage.urgency",
     "Classify the urgency of this support ticket as exactly one of P1, P2, P3.",
     "gpt-4o", 1.0, cs_triage, 0.03, (620, 780), (2, 4), (780, 1450), 0.95),
    ("route.team",
     "Route this message to exactly one team: billing, platform, security, onboarding.",
     "gpt-4o", 0.0, cs_route, 0.02, (540, 700), (2, 5), (700, 1300), 0.85),
    ("lang.detect",
     "Identify the ISO language code of the message. Answer with the code only.",
     "gpt-4o-mini", None, cs_lang, 0.01, (180, 260), (1, 3), (240, 520), 0.70),
    ("extract.order_id",
     "Extract the order number referenced in the message. Digits only.",
     "gpt-4o-mini", 0.0, cs_extract, 0.01, (200, 300), (2, 6), (260, 560), 0.60),
    ("summarize.thread",
     "Summarize this support thread in one sentence for the agent handoff note.",
     "gpt-4o", 0.7, cs_summarize, 0.0, (1400, 2600), (28, 52), (1900, 3600), 0.50),
    ("draft.reply",
     "Draft a customer-facing reply. Match our tone guide and never promise a refund.",
     "claude-opus-5", 0.6, cs_draft, 0.0, (1800, 3200), (60, 120), (2600, 5200), 0.45),
    ("sentiment.gate",
     "Return the sentiment of the message as positive, neutral, or negative.",
     "gpt-4o-mini", 0.0, cs_sentiment, 0.0, (210, 280), (1, 2), (250, 480), 0.55),
]

GROUND_TRUTH = {
    "triage.urgency": "TIGHT",
    "route.team": "PARTIAL",
    "lang.detect": "TIGHT",
    "extract.order_id": "TIGHT",
    "summarize.thread": "LOOSE",
    "draft.reply": "LOOSE",
    "sentiment.gate": "DEGENERATE",
}

# a pool of inputs deliberately reused, so conditional entropy is measurable
# from production traffic alone (duplicate tickets, retries, recurring queries)
REPEAT_RATE = 0.12


def perturb(label: str, options: list[str], noise: float) -> str:
    """Sampling noise: with probability `noise` the model returns a wrong label."""
    if noise and RNG.random() < noise:
        alt = [o for o in options if o != label]
        if alt:
            return RNG.choice(alt)
    return label


def main(n_traces: int = 520):
    traces = []
    seen_inputs: dict[str, list[str]] = {name: [] for name, *_ in CALL_SITES}
    label_space: dict[str, set] = {name: set() for name, *_ in CALL_SITES}
    resample_pool: dict[str, list[tuple[str, str]]] = {name: [] for name, *_ in CALL_SITES}
    cursor = T0

    for t in range(n_traces):
        trace_id = IDS.trace()
        root_id = IDS.span()
        spans = []
        children = []
        cursor += timedelta(seconds=RNG.randint(20, 240))
        span_start = cursor + timedelta(milliseconds=20)

        for (name, sysp, model, temp, gen, noise, ptok_r, ctok_r, ms_r, weight) in CALL_SITES:
            if RNG.random() > weight:
                continue
            # reuse a previously seen input sometimes
            if seen_inputs[name] and RNG.random() < REPEAT_RATE:
                user = RNG.choice(seen_inputs[name])
                _, truth = gen()          # advance rng consistently
                truth = None
            else:
                user, truth = gen()
                if len(seen_inputs[name]) < 400:
                    seen_inputs[name].append(user)

            # recompute the label for a reused input by replaying its generator
            if truth is None:
                truth = _label_for(name, user)

            label_space[name].add(truth)
            out = perturb(truth, sorted(label_space[name]), noise)
            ms = RNG.uniform(*ms_r)
            span = synth.make_span(
                trace_id=trace_id, span_id=IDS.span(), parent_span_id=root_id,
                name="ChatCompletion", kind="LLM", start=span_start, duration_ms=ms,
                flat_attrs=synth.llm_attrs(
                    model=model, system=sysp, user=user, output=out,
                    prompt_tokens=RNG.randint(*ptok_r), completion_tokens=RNG.randint(*ctok_r),
                    temperature=temp, node_id=name),
                session_id=f"sess_{t // 4:04d}", user_id=f"user-{t % 60}")
            children.append(span)
            span_start += timedelta(milliseconds=ms + 6)
            if len(resample_pool[name]) < 60 and RNG.random() < 0.2:
                resample_pool[name].append((user, truth))

        if not children:
            continue
        total_ms = (span_start - cursor).total_seconds() * 1000 + 30
        root = synth.make_span(
            trace_id=trace_id, span_id=root_id, name="triage-agent.run", kind="AGENT",
            start=cursor, duration_ms=total_ms,
            flat_attrs=synth.root_attrs(
                question="[inbound support ticket]",
                answer="[handled]",
                agent="triage-agent",
                metadata={"queue": "tier1", "corpus_day": 1}),
            session_id=f"sess_{t // 4:04d}", user_id=f"user-{t % 60}")
        spans = [root] + children
        traces.append({"trace_id": trace_id, "root_span_id": root_id, "spans": spans})

    # resamples: same input through the same model three times
    resamples = {}
    for (name, _s, _m, _t, gen, noise, *_rest) in CALL_SITES:
        rows = []
        for user, truth in resample_pool[name]:
            opts = sorted(label_space[name])
            rows.append({"input": user,
                         "outputs": [perturb(truth, opts, noise) for _ in range(3)]})
        resamples[name] = rows

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    corpus_path = os.path.join(HERE, "out", "corpus.json")
    with open(corpus_path, "w") as fh:
        json.dump(traces, fh, separators=(",", ":"))
        fh.write("\n")
    with open(os.path.join(HERE, "out", "resamples.json"), "w") as fh:
        json.dump(resamples, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(HERE, "out", "corpus.meta.json"), "w") as fh:
        json.dump({
            "seed": SEED,
            "traces": len(traces),
            "llm_spans": sum(len(t["spans"]) - 1 for t in traces),
            "corpus_window": "1 day (extrapolate x30 for monthly projections)",
            "ground_truth": GROUND_TRUTH,
            "notes": "Labels are the generator's intent, not a model's opinion. "
                     "Sampling noise was injected per call site to make the "
                     "self-agreement measurement non-trivial.",
        }, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(HERE, "out", "sample_trace.json"), "w") as fh:
        json.dump(traces[0], fh, indent=1)
        fh.write("\n")

    print(f"{len(traces)} traces, {sum(len(t['spans']) - 1 for t in traces)} LLM spans "
          f"-> out/corpus.json ({os.path.getsize(corpus_path) / 1e6:.1f} MB)")
    for name in GROUND_TRUTH:
        n = sum(1 for t in traces for s in t["spans"]
                if (s.get("attributes", {}).get("graph", {}).get("node", {}).get("id")) == name)
        print(f"  {name:<18} {n:>5} calls   truth={GROUND_TRUTH[name]}")


def _label_for(name: str, user: str) -> str:
    """Recover the intended label for a reused input, deterministically."""
    if name == "triage.urgency":
        body = user.replace("[ticket] ", "")
        return "p1" if body in P1 else "p2" if body in P2 else "p3"
    if name == "route.team":
        for team, kws in TEAM.items():
            if any(k in user for k in kws):
                return team
        return RNG.choice(list(TEAM))
    if name == "lang.detect":
        for code, samples in LANG.items():
            if user in samples:
                return code
        return "en"
    if name == "extract.order_id":
        import re
        m = re.search(r"#(\d+)", user)
        return m.group(1) if m else "0"
    if name == "sentiment.gate":
        return "neutral"
    if name == "summarize.thread":
        return f"{RNG.choice(SUM_OPEN)} {RNG.choice(SUM_MID)} {RNG.choice(SUM_TAIL)}"
    return f"{RNG.choice(REPLY_OPEN)} — {RNG.choice(REPLY_MID)} {RNG.choice(REPLY_TAIL)}"


if __name__ == "__main__":
    main()
