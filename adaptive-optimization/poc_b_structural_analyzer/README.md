# POC B — Structural Analyzer

**The bet: the highest-precision optimization isn't substitution, it's deletion.**

Structure is observable in a single trace; distribution is not. That makes these the only
findings available on day one for an agent with no history — and the `PROVABLE` class
carries no correctness risk at all, because nothing reads the values being removed.

No corpus. No model. No statistics. No eval.

```bash
python3 generate_traces.py && python3 run.py
```

## The five detectors

Each asks a question a compiler would ask, not one a statistician would.

| Pattern | Question | Class |
|---|---|---|
| `dead_llm_call` | is this value ever read? | **PROVABLE** |
| `redundant_call` | is this work repeated in-trace? | **PROVABLE** |
| `verbatim_dispatch` | is this argument derived or copied? | LOCAL |
| `passthrough_reformat` | does this call add information? | LOCAL |
| `rebuilt_prefix` | is this context re-sent? | ADVISORY |

**PROVABLE** — safe the way dead-code elimination is safe. No guard, no replay, no eval.
**LOCAL** — provable inside the trace, but substitution still needs the call site to
behave this way in general, so it hands off to POC A first. **ADVISORY** — a caching or
config change; no generated code at all.

`dead_llm_call` counts the trace answer as a consumer and treats a tool call as read only
if a matching TOOL span actually ran. `verbatim_dispatch` fires only when **every**
argument appears verbatim — a dispatch mixing one copied and one derived argument is real
work, and substituting it would silently drop the derivation.

## Results

```
pattern                 planted  detected    TP    FP    FN  precision   recall      class
dead_llm_call                40        40    40     0     0      1.000    1.000   PROVABLE
passthrough_reformat         40        40    40     0     0      1.000    1.000      LOCAL
rebuilt_prefix               30        30    30     0     0      1.000    1.000   ADVISORY
redundant_call               30        30    30     0     0      1.000    1.000   PROVABLE
verbatim_dispatch            40        40    40     0     0      1.000    1.000      LOCAL
overall                                     180     0     0      1.000    1.000

clean controls: 110, of which 0 produced a false finding (0.0%)
```

Value, graded by the evidence it needs:

```
PROVABLE     70 findings   $  0.077 ( 9.3% of spend)      50.2s latency removed
LOCAL        80 findings   $  0.104 (12.6% of spend)      65.2s latency removed
ADVISORY     30 findings   $  0.015 ( 1.8% of spend)
```

## Controls

110 of 290 traces are clean, and 50 of those are **deliberate near-misses** designed to
break a naive detector:

- `near_miss_answer_only` — an LLM computes a figure read by nothing except the final
  answer. A naive dead-call detector flags it; this one must not.
- `near_miss_partial_args` — a dispatch with one copied and one genuinely derived
  argument. Must not be flagged as verbatim dispatch.

Precision holds against both, which is what makes the 1.000 mean anything.

## Caveats

I wrote the planter and the detectors, so 1.000/1.000 demonstrates that the plumbing is
sound, not that the detectors survive real traces. Real agents will have messier
dataflow: values that reach a consumer through serialization the token overlap misses,
outputs consumed by a sibling rather than a descendant, tool results mutated between
spans. Expect precision to be the number that moves first, and it is the one to protect.
