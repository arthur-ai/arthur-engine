# POC A — Tightness Profiler

**The bet: measure before you generate.** Corpus in, grouped by call site; profile with
arithmetic; measure how tightly the output depends on the input; only then let a judge
write code; then decide from replay rather than from the judge's opinion.

```bash
python3 generate_corpus.py && python3 run.py
python3 run.py --judge model     # real Claude judge; needs ANTHROPIC_API_KEY
```

## Pipeline

**Step 1 — profile arithmetically.** Group 2,340 LLM spans into call sites, keyed by a
hash of the invariant prompt prefix plus `graph.node.id`. `span_name` is useless as
identity — every OpenAI span is called `ChatCompletion`. Rank by the union of top-N by
cost, by cumulative latency, and by call volume. Cost alone is the wrong lens: a cheap
call made 400 times a day on the critical path is a latency and consistency target that
rounds to zero dollars.

**Step 2 — measure tightness.** Tight means low `H(output | input)`. The trap is that
**marginal** entropy is a useless filter: `extract.order_id` emits a different order
number nearly every call (8.04 bits marginal) and is perfectly tight. Only the conditional
quantity separates the two, and measuring it needs the same input more than once — from
repeated inputs in production traffic, or from resampling recorded inputs through the
same model.

Temperature is a **confound, not a signal**. A tight function at temperature 1.0 shows
inflated conditional entropy without being loose, so it is controlled for rather than
ranked by. Absence of a `temperature` key is recorded as absence, because a caller who
never passed one told us nothing about their intent.

Step 2's verdict is deliberately only `CANDIDATE` / `LOOSE` / `DEGENERATE` / `UNKNOWN`.
Whether a candidate is *tight* or *partial* is a claim about how much of the input space
a guard can cover, so it cannot honestly be made before the guard exists.

**Step 2b — config findings.** A tight call site running at a temperature nobody chose
needs no script: setting it to 0 delivers consistency for free.

**Step 3 — judge proposes, replay disposes.** The judge writes `fast_path` and `guard`.
Its confidence is discarded. The score comes from replaying against recorded outputs on a
**chronological** holdout (a random split leaks: repeated inputs would land on both sides
and flatter the guard).

Promotion requires the fast path to be **not significantly less consistent than the model
it replaces**, by a one-sided two-proportion test against the model's own self-agreement.
A bare inequality makes the decision a coin flip in the noise band — `triage.urgency`
scored 0.973 against a self-agreement of 0.974, and treating that 0.001 as evidence would
have rejected a good candidate on sample-size luck.

**Step 4 — score the decisions.** Screening accuracy (precision-critical) is scored
separately from coverage (a property of the code generator). Conflating them makes the
measurement look wrong when the real limitation is the synthesizer.

## Results

```
call site               n distinct  H(out)  H(out|in)  self-agree  tight-mass     verdict
draft.reply           223      103    6.51      3.674       0.125       0.000       LOOSE
summarize.thread      258      160    7.18      1.213       0.454       0.000       LOOSE
triage.urgency        489        3    1.47      0.196       0.974       0.315   CANDIDATE
route.team            439        4    1.99      0.289       0.947       0.768   CANDIDATE
extract.order_id      317      277    8.04      0.032       0.984       0.966   CANDIDATE
lang.detect           353        5    2.31      0.076       0.990       0.677   CANDIDATE
sentiment.gate        261        1    0.00      0.000       1.000       1.000  DEGENERATE
```

Screening **7/7**. Four promoted, **0 false promotions**. `draft.reply` — 77% of total
spend — was rejected before a line of code was written, because the model agrees with
itself only 12.5% of the time there. `sentiment.gate` returns `"neutral"` on all 261
calls: not a script candidate, a dead call, handed to POC B.

Artifacts land in `out/` as `(script, guard, fallback)` tuples with their evidence
attached, plus standalone `fastpath_*.py` files.

## Corpus

`generate_corpus.py` builds 520 traces / 2,340 LLM spans across seven call sites spanning
the whole spectrum, with `ground_truth` recorded in `out/corpus.meta.json` so the POC is
scored rather than eyeballed. ~12% of inputs are deliberately repeated so conditional
entropy is measurable from traffic alone, and `out/resamples.json` supplies three
same-input runs per sampled call.

Deliberate traps: the most expensive call site must be rejected; one tight site runs at an
accidental temperature; one site is high-cardinality but tight; one is degenerate.

## Caveats

Synthetic data with known ground truth, and I wrote both the generator and the analyzer.
The coverage shortfall on `route.team` (84%) is the synthesizer's limit, not the
measurement's — an LLM judge would likely write better rules, which is what `--judge
model` is for. Loosening the judge is safe precisely because promotion is gated
downstream by replay.
