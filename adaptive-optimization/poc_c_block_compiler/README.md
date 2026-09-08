# POC C — Block Compiler + Shadow Harness

**The bet: take the big prize, and make the rollout survivable.**

A single span swapped for a script saves one call. The press release's "eleven steps and
two of them doing real work" needs whole *blocks* to collapse — which means reasoning
about a subgraph, not an I/O mapping. Then it needs a way to deploy that without a
customer finding out the hard way.

```bash
python3 generate_corpus.py && python3 run.py
```

## Pipeline

**Step 1 — mine recurring blocks.** Every contiguous window of sibling spans, keyed by
its call-site signature, counted and costed. The winner is the commonest agent idiom
there is:

```
LLM(block.dispatch) -> TOOL(lookup_order) -> LLM(block.render)     260 occurrences
```

**Step 2 — compile it.** The tool call is real work and is **preserved**; `call_tool` is
injected rather than reimplemented. The two model calls become an argument extraction and
a template render. The template is recovered by substituting tool-result values back out
of the recorded reply, with each field's **transform voted across all 260 windows**.

Because the tool call is retained, the guard covers the *extraction* rather than the whole
block — what has to be safe is deriving the tool's arguments.

**Step 3 — replay.** 100% coverage, 100% agreement over the baseline phase. Two model
calls per occurrence eliminated.

**Step 4 — shadow mode.** Nothing is switched on at promotion time. The compiled block
runs in parallel, its output discarded, for an 8-day warmup that establishes a baseline.
Two independent monitors then run forever, because they see different failures.

## The two monitors, and why both are mandatory

```
 day         phase   seen  coverage  sampled  agreement  state
   8      baseline     26    100.0%        5     100.0%  PROMOTED
  10   input_drift     26     53.8%        2     100.0%  PROMOTED  <- coverage alert
  13   input_drift     26     30.8%        1     100.0%  PROMOTED  <- coverage alert
  15  output_drift     26    100.0%        5       0.0%  DEMOTED  <- AGREEMENT ALERT
  19  output_drift     26    100.0%        5       0.0%  DEMOTED  <- AGREEMENT ALERT
```

**Coverage monitor** — the guard's accept rate. On days 10–14 a new intake channel starts
sending inputs with no order number, and coverage falls 100% → 31% while agreement holds
at 100%. This is the *safe* failure: rejected traffic already falls back to the model, so
the bill rises and quality doesn't move.

**Sampling monitor** — agreement on the 20% of guarded traffic that keeps going to the
model anyway. On day 15 someone changes the reply format upstream. Inputs still look
completely familiar, coverage stays at 100%, and the compiled template is now wrong on
every call. **The guard cannot see this by construction** — it inspects inputs, and the
inputs didn't change. Only sampling catches it, which is why the sampling slice is a
permanent operating cost of running a fast path, not a rollout phase you graduate from.

This is also the honest answer to cold start: shadow mode turns "no history" into "history
in a week", starting the guard tight and widening it as real traffic confirms.

## The bug worth reporting

The first template inference produced `"Order {order_id} is {status} and arrives {eta}."`
— which looks correct, and is wrong on every value containing an underscore, because the
model wrote `in transit` where the tool returned `in_transit`. Replay scored it **51.2%**
and refused to promote.

Nothing about *reading* that artifact would have revealed the problem. The gate did. The
fix was to vote each field's transform across all windows rather than take it from the
first window that happened to parse — a value with no underscore matches `identity` and
`spaces` alike, so a single observation cannot distinguish them.

## Caveats

One block shape, one template family, synthetic drift injected on a schedule I chose. Real
drift is gradual and partial rather than a step change on a known day, and the alert
thresholds here (15 points of coverage, 5 points of agreement) are guesses that would
need calibrating against a real traffic baseline. The miner also enumerates all windows
of length 2–4 over sibling spans, which is fine at this scale and would need indexing at
production volume.
