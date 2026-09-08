#!/usr/bin/env python3
"""POC C end to end: mine a block, compile it, replay it, then shadow it."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from _common import spanmodel as sm   # noqa: E402
import blocks as bl                    # noqa: E402
import shadow as sh                    # noqa: E402

OUT = os.path.join(HERE, "out")
BAR = "=" * 98


def rule(t):
    print(f"\n{BAR}\n{t}\n{BAR}")


def main() -> int:
    traces = sm.load_corpus(os.path.join(OUT, "stream.json"))
    meta = json.load(open(os.path.join(OUT, "stream.meta.json")))
    baseline = [t for t in traces if t["_phase"] == "baseline"]

    rule("STEP 1  mine recurring blocks (baseline phase only — no drift yet)")
    found = bl.mine(baseline)
    print(bl.format_table(found))
    target = next((b for b in found if b.llm_calls >= 2 and "TOOL" in b.kinds), None)
    if target is None:
        print("no multi-LLM block with a tool call found")
        return 1
    print(f"\ntarget: {' -> '.join(target.labels)}")
    print(f"  {target.occurrences} occurrences, {target.llm_calls} LLM calls each, "
          f"${target.cost_usd:.3f} over the baseline phase")
    print(f"  mean latency {target.latency_ms / target.occurrences:.0f}ms per occurrence")

    rule("STEP 2  compile the block")
    compiled = bl.compile_block(target)
    if compiled is None:
        print("could not infer a template — the render call is not deterministic")
        return 1
    print(f"recovered template: {compiled['template']!r}")
    print(f"  field transforms:  {json.dumps(compiled['fields'])}")
    print(f"  {compiled['note']}")
    print(f"  preserved tool call: {compiled['tool']} (real work, kept)")
    print(f"  model calls eliminated per occurrence: {compiled['llm_calls_removed']}")
    print("\n--- generated artifact ---")
    print(compiled["source"])

    rule("STEP 3  replay against the baseline phase")
    scored = bl.replay_block(target, compiled, target.examples)
    print(f"windows={scored['windows']}  guard admits={scored['coverage']:.1%}  "
          f"agreement={scored['agreement']:.1%}")
    for m in scored["misses"]:
        print(f"  miss: produced {m['produced']!r}\n        expected {m['expected']!r}")
    if scored["agreement"] < 0.95 or scored["coverage"] < 0.5:
        print("\nnot promotable on replay — stopping before shadow")
        return 0
    print("\npromotable on replay. Nothing is switched on yet: the next step runs it in\n"
          "parallel over the live stream and decides from evidence.")

    rule("STEP 4  shadow mode over the full 20-day stream")
    print(f"expected: {json.dumps(meta['expected'], indent=2)}\n")
    run = sh.ShadowRun(compiled, sample_rate=0.20, warmup_days=8)
    current_day = None
    for trace in traces:
        day = trace["_day"]
        if current_day is not None and day != current_day:
            run.close_day(current_day)
        current_day = day
        window = [s for s in sm.spans_in_start_order(trace) if s.get("parentSpanId")]
        tool_span = next((s for s in window if sm.span_kind(s) == "TOOL"), None)
        llms = [s for s in window if sm.span_kind(s) == "LLM"
                and sm.call_site_label(s) in ("block.dispatch", "block.render")]
        if tool_span is None or len(llms) < 2:
            continue
        result = sm.get(sm.attrs(tool_span), "output.value")
        if isinstance(result, str):
            result = json.loads(result)
        run.observe(day, trace["_phase"], sm.input_text(llms[0]), result,
                    str(sm.output_payload(llms[-1]) or ""))
    if current_day is not None:
        run.close_day(current_day)

    print(run.timeline())
    rule("ALERTS")
    for a in run.alerts:
        print(f"  day {a.day:>2}  [{a.kind}] {a.message}")
        print(f"           action: {a.action}\n")
    print(f"final state: {run.state}")

    with open(os.path.join(OUT, "block_artifact.py"), "w") as fh:
        fh.write(f'"""Compiled block: {" -> ".join(target.labels)}.\n\n'
                 f'{compiled["note"]}. Replay over the baseline phase: '
                 f'coverage {scored["coverage"]:.1%}, agreement {scored["agreement"]:.1%}.\n'
                 f'Eliminates {compiled["llm_calls_removed"]} model calls per occurrence and '
                 f'preserves the {compiled["tool"]} call.\n"""\n\nimport re\n\n\n')
        fh.write(compiled["source"])
    with open(os.path.join(OUT, "shadow_report.json"), "w") as fh:
        json.dump({
            "block": list(target.labels),
            "occurrences_baseline": target.occurrences,
            "replay": {k: v for k, v in scored.items() if k != "misses"},
            "baseline_coverage": run.baseline_coverage,
            "baseline_agreement": run.baseline_agreement,
            "final_state": run.state,
            "alerts": [a.__dict__ for a in run.alerts],
            "daily": [{"day": w.day, "phase": w.phase, "seen": w.seen,
                       "coverage": round(w.coverage, 4),
                       "sampled": w.sampled,
                       "sampled_agreement": (round(w.sampled_agreement, 4)
                                             if w.sampled_agreement is not None else None)}
                      for w in sorted(run.windows.values(), key=lambda x: x.day)],
        }, fh, indent=2)
        fh.write("\n")
    print("\nwrote out/block_artifact.py and out/shadow_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
