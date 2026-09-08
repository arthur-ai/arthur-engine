# Adaptive Optimization — three candidate POCs

Three different bets on the same problem, built so they can be compared rather than
assembled. Each is self-contained, stdlib-only, and runs in a few seconds:

```bash
cd poc_a_tightness_profiler   && python3 generate_corpus.py && python3 run.py
cd poc_b_structural_analyzer  && python3 generate_traces.py && python3 run.py
cd poc_c_block_compiler       && python3 generate_corpus.py && python3 run.py
```

All three consume spans in the engine's normalized `arthur_span_v1` shape — the same
nested OpenInference attributes stored in `DatabaseSpan.raw_data` — so nothing here
assumes a data format the platform doesn't already have.

| | POC A · Tightness Profiler | POC B · Structural Analyzer | POC C · Block Compiler + Shadow |
|---|---|---|---|
| **Bet** | Measure before generating | Deletion beats substitution | Collapse whole blocks, roll out safely |
| **Input** | A corpus grouped by call site | One trace at a time | A time-ordered stream |
| **Needs history?** | Yes — hundreds of calls per site | **No** | Yes for mining, no for monitoring |
| **Unit optimized** | A single call site | A single span (or its deletion) | A 3-span block |
| **Uses an LLM?** | Yes, to write the script | **No** | No |
| **Correctness risk** | Guarded, replay-gated | Zero for `PROVABLE` findings | Guarded, replay-gated, then shadowed |
| **Answers** | Can we find and *prove* candidates? | Can we deliver value on day one? | Can we take the big prize and survive drift? |

## What each one actually established

**POC A** — 7 call sites profiled, **7/7 screened correctly**, 4 fast paths promoted,
**0 false promotions**. The two genuinely loose call sites were rejected before any code
was generated, including `draft.reply`, which is **77% of all spend**. Ranking by cost
alone would have sent the biggest cost centre straight to a code generator.

It also produced a finding that needs no script at all: `triage.urgency` is a tight
function running at temperature 1.0, which nobody chose. Setting it to 0 removes
avoidable variance for free.

**POC B** — 290 traces, **precision 1.000, recall 1.000**, and **0 false findings across
110 clean controls**, 50 of which are deliberate near-misses (a value read only by the
final answer; a dispatch with one copied and one derived argument). 9.3% of spend and 50
seconds of latency sit in `PROVABLE` findings — dead calls and in-trace duplicates that
can be deleted with no guard, no replay, and no eval.

**POC C** — mined a `dispatch → tool → render` block occurring 260 times, recovered its
template, and eliminated **2 of 3 model calls** while preserving the tool call. Then
shadow mode over 20 days caught both drift classes with the right monitor:

- days 10–14, the input distribution moves → **coverage falls 100% → 31%**, agreement
  holds. Savings shrink; quality doesn't move.
- days 15–19, the reply format changes upstream → **coverage stays 100%, sampled
  agreement falls to 0%** → demote. The guard is blind to this by construction.

## Two bugs worth reporting, because the gates caught them

Both were caught by the machinery rather than by inspection, which is the main thing
these POCs were built to test.

1. **POC A's synthesizer starved a whole label.** A global purity-ranked cap on keyword
   rules left `lang.detect` with zero German keywords, so the guard rejected 100% of
   German traffic. Fixed by greedy set cover per label, then by calibrating the purity
   bar to the call site's measured noise floor — a fixed 0.95 bar discards a perfect
   keyword whose observed purity is 0.93 because two sampled labels flipped.

2. **POC C inferred a template that was wrong 49% of the time.** It recovered
   `"Order {order_id} is {status}…"` but formatted the raw `in_transit` where the model
   had written `in transit`. Replay caught it at 51.2% agreement and refused to promote.
   Fixed by voting each field's transform across all windows instead of taking it from
   the first window that parsed.

The second one is the load-bearing result. A plausible-looking generated artifact was
wrong half the time, and *nothing about reading it* would have revealed that. The replay
gate did.

## Recommendation

**Ship B first, A second, C as the destination.** B needs no history, carries no
correctness risk on its `PROVABLE` class, and gives a customer a number in their first
session. A is the engine — the measurement discipline everything else depends on. C is
what the press release actually promises, and its shadow harness is the only component
that makes the continuous-monitoring claim real.

They compose in that order too: B's `LOCAL` findings are exactly the candidates A should
confirm, and A's promoted call sites are what C's shadow harness should be watching.

## Honest limitations

- **The data is synthetic and I wrote both the generators and the analyzers.** POC B's
  1.000/1.000 means the plumbing is sound, not that the detectors survive real traces.
  Every number here is a statement about the machinery, not about any customer's agent.
- **The judge is stubbed by default.** `_common/judge.py` ships an offline deterministic
  synthesizer so everything runs with no key. Pass `--judge model` (with
  `ANTHROPIC_API_KEY` and the `anthropic` package) to use a real Claude judge. The
  measurement and promotion machinery is identical either way — that separation is the
  point, since the judge is never trusted.
- **Prices are illustrative.** `ILLUSTRATIVE_PRICES_USD_PER_MTOK` in
  `_common/spanmodel.py` is a placeholder rate card. Swap in real rates before quoting
  savings to anyone.
- **Generated code is `exec`'d in a bare namespace.** Fine for a POC, unacceptable in
  production: real deployment ships the source for human review, or sandboxes it with no
  imports, no filesystem, and a wall-clock budget.
- **Nothing here touches the inline/advisory question.** All three emit artifacts. Who
  executes them — Arthur in-path, or the customer in their own repo — is still open, and
  it changes what the artifact should be.

## Layout

```
_common/
  spanmodel.py   read arthur_span_v1 spans; call-site keying; cost model
  synth.py       build synthetic spans in the normalized shape
  judge.py       OfflineSynthesizer | ModelJudge behind one interface
poc_a_tightness_profiler/
  generate_corpus.py  7 call sites, ground truth, resample fixture
  profile.py          arithmetic profiling: cost / latency / volume
  tightness.py        H(output|input), self-agreement, screening verdict
  compile_candidate.py judge + replay + guard + statistical promotion rule
poc_b_structural_analyzer/
  generate_traces.py  5 planted patterns + 110 controls
  dataflow.py         5 detectors, graded PROVABLE / LOCAL / ADVISORY
poc_c_block_compiler/
  generate_corpus.py  20-day stream, 3 phases, 2 drift classes
  blocks.py           subgraph mining, template inference, replay
  shadow.py           coverage monitor + sampling monitor + promote/demote
```
