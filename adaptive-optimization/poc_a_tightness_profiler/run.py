#!/usr/bin/env python3
"""POC A end to end.

  profile arithmetically -> measure tightness -> judge proposes -> replay disposes
  -> emit (script, guard, fallback) -> score the classifier against ground truth

    python3 run.py                 # offline synthesizer as the judge (default)
    python3 run.py --judge model   # real Claude judge (needs ANTHROPIC_API_KEY)
"""

import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from _common import spanmodel as sm            # noqa: E402
from _common.judge import get_judge            # noqa: E402
import profile as prof                          # noqa: E402
import tightness as tt                          # noqa: E402
import compile_candidate as cc                  # noqa: E402

OUT = os.path.join(HERE, "out")
BAR = "=" * 96


def rule(title: str) -> None:
    print(f"\n{BAR}\n{title}\n{BAR}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", choices=["offline", "model"], default="offline")
    ap.add_argument("--top-n", type=int, default=5,
                    help="top call sites per ranking (cost / latency / volume)")
    args = ap.parse_args()

    corpus_path = os.path.join(OUT, "corpus.json")
    if not os.path.exists(corpus_path):
        print("corpus missing — run generate_corpus.py first", file=sys.stderr)
        return 1

    traces = sm.load_corpus(corpus_path)
    meta = json.load(open(os.path.join(OUT, "corpus.meta.json")))
    resamples = json.load(open(os.path.join(OUT, "resamples.json")))
    truth = meta["ground_truth"]

    # ── step 1: arithmetic ────────────────────────────────────────────────────
    rule("STEP 1  profile arithmetically (no model calls)")
    profiles = prof.profile_corpus(traces)
    total_cost = sum(p.cost_usd for p in profiles)
    print(f"{len(traces)} traces | {sum(p.calls for p in profiles)} LLM calls | "
          f"${total_cost:.2f} for the corpus window ({meta['corpus_window']})\n")
    print(prof.format_table(profiles, total_cost))

    hot_pairs = prof.hot_spots(profiles, args.top_n)
    hot = [p for p, _why in hot_pairs]
    why_by_key = {p.key: why for p, why in hot_pairs}
    print(f"\n{len(hot)} of {len(profiles)} call sites selected "
          f"({100 * sum(p.cost_usd for p in hot) / total_cost:.1f}% of spend, "
          f"{100 * sum(p.calls for p in hot) / sum(p.calls for p in profiles):.1f}% of calls) "
          f"-> only these go to the judge.")
    for p in hot:
        print(f"    {p.label:<18} selected by: {', '.join(why_by_key[p.key])}")

    # index spans by call site for the later steps
    spans_by_key: dict[str, list[dict]] = defaultdict(list)
    for _tr, span in sm.iter_llm_spans(traces):
        spans_by_key[sm.call_site_key(span)].append(span)

    # ── step 2: tightness ─────────────────────────────────────────────────────
    rule("STEP 2  measure tightness — H(output | input), still no judge")
    rows, tight_by_key, final_verdict = [], {}, {}
    for p in hot:
        row = tt.measure(p.label, spans_by_key[p.key], resamples.get(p.label))
        rows.append(row)
        tight_by_key[p.key] = row
    print(tt.format_table(rows))
    print("\nwhy:")
    for r in rows:
        print(f"  {r.label:<18} {r.reason}")

    # the free finding: a tight call site whose temperature was never a decision
    rule("STEP 2b  config findings that need no script at all")
    found_any = False
    for p in hot:
        r = tight_by_key[p.key]
        if r.verdict == "CANDIDATE" and (p.temperature or 0) > 0:
            found_any = True
            print(f"  {p.label}: tight function running at temperature {p.temperature:g}.")
            print(f"    Setting it to 0 removes {r.marginal_bits - (r.conditional_bits or 0):.2f} "
                  f"bits of avoidable variance. Zero implementation, zero correctness risk,")
            print(f"    and it delivers consistency on its own. Model self-agreement here is "
                  f"{r.self_agreement:.3f}.")
    if not found_any:
        print("  none")

    # ── step 3: judge + replay ────────────────────────────────────────────────
    judge = get_judge(args.judge)
    rule(f"STEP 3  judge proposes ({judge.name}), replay disposes")
    results, artifacts = [], []
    for p in hot:
        r = tight_by_key[p.key]
        if r.verdict in ("LOOSE", "DEGENERATE", "UNKNOWN"):
            print(f"\n  {p.label:<18} SKIPPED before judging — {r.verdict}")
            print(f"    {r.reason}")
            results.append((p, r, None))
            final_verdict[p.label] = r.verdict
            continue
        res = cc.compile_and_replay(p.label, spans_by_key[p.key], judge,
                                    r.self_agreement, r.self_agreement_n)
        results.append((p, r, res))
        # TIGHT vs PARTIAL is a statement about how much of the input space the
        # guard admits, so it cannot be settled before the guard exists.
        final_verdict[p.label] = cc.refine_verdict(res)
        verdict = "PROMOTE" if res.promoted else "REJECT"
        delta = res.consistency_delta
        print(f"\n  {p.label:<18} {verdict}   strategy={res.strategy}")
        print(f"    train={res.n_train}  holdout={res.n_holdout}  "
              f"coverage={res.coverage:.1%}  agree(in-guard)={res.agreement_in_guard:.3f}  "
              f"agree(no-guard)={res.agreement_overall:.3f}")
        if delta is not None:
            better = "more" if delta >= 0 else "less"
            print(f"    model self-agreement={res.self_agreement:.3f} -> fast path is "
                  f"{abs(delta):.3f} {better} consistent than the model it replaces")
        print(f"    {res.decision_reason}")
        if res.mismatches:
            m = res.mismatches[0]
            print(f"    example miss: {m['input'][:70]!r} -> got {m['got']!r}, "
                  f"recorded {m['expected']!r}")

        if res.promoted and res.proposal:
            savings = cc.projected_savings(res, p.cost_per_call, p.calls)
            art = {
                "call_site": p.label,
                "call_site_key": p.key,
                "model_replaced": p.model,
                "strategy": res.strategy,
                "rationale": res.proposal.rationale,
                "script": res.proposal.source,
                "guard": res.proposal.guard_source,
                "fallback": {"action": "call_model", "model": p.model,
                             "when": "guard returns False, script returns None, or "
                                     "the sampling slice is selected"},
                "evidence": {
                    "holdout_calls": res.n_holdout,
                    "coverage": round(res.coverage, 4),
                    "agreement_in_guard": round(res.agreement_in_guard, 4),
                    "model_self_agreement": round(res.self_agreement, 4)
                    if res.self_agreement is not None else None,
                    "model_self_agreement_n": res.self_agreement_n,
                    "z_vs_model": round(res.z_vs_model, 3),
                    "conditional_bits": round(r.conditional_bits, 4)
                    if r.conditional_bits is not None else None,
                },
                "projected_monthly": savings,
            }
            artifacts.append(art)

    # ── step 4: score the classifier ─────────────────────────────────────────
    rule("STEP 4  score the decisions against ground truth")
    print("4a. SCREENING — did step 2 send the right call sites to the judge?")
    print("    This is the precision-critical call: promoting a LOOSE or DEGENERATE site is")
    print("    the outcome that costs customer trust.\n")
    print(f"    {'call site':<19}{'truth':<12}{'screened':<12}{'correct':>9}")
    print("    " + "-" * 51)
    screen_ok = 0
    for p_ in hot:
        exp = truth.get(p_.label, "?")
        should_judge = exp in ("TIGHT", "PARTIAL")
        did_judge = tight_by_key[p_.key].verdict == "CANDIDATE"
        ok = should_judge == did_judge
        screen_ok += ok
        print(f"    {p_.label[:18]:<19}{exp:<12}"
              f"{('CANDIDATE' if did_judge else tight_by_key[p_.key].verdict):<12}"
              f"{('yes' if ok else 'NO'):>9}")
    print(f"\n    screening accuracy: {screen_ok}/{len(hot)}")

    false_promotes = [a for a in artifacts
                      if truth.get(a["call_site"]) in ("LOOSE", "DEGENERATE")]
    print(f"    false promotions (a LOOSE/DEGENERATE site promoted): {len(false_promotes)}")
    if false_promotes:
        print("    *** precision failure — the outcome that costs customer trust ***")

    print("\n4b. COVERAGE — how much of each tight call site did the guard actually reach?")
    print("    A shortfall here is a limitation of the code generator, not of the")
    print("    measurement, and it costs recall (missed savings) rather than trust.\n")
    print(f"    {'call site':<19}{'truth':<12}{'coverage':>10}{'headroom':>10}")
    print("    " + "-" * 51)
    for p_, r_, res_ in results:
        if res_ is None or not res_.promoted:
            continue
        exp = truth.get(p_.label, "?")
        ideal = 1.0 if exp == "TIGHT" else 0.85 if exp == "PARTIAL" else 0.0
        print(f"    {p_.label[:18]:<19}{exp:<12}{res_.coverage:>9.1%}"
              f"{max(0.0, ideal - res_.coverage):>10.1%}")

    total_saving = sum(a["projected_monthly"]["gross_saving_usd"] for a in artifacts)
    residual = sum(a["projected_monthly"]["residual_model_spend_usd"] for a in artifacts)
    rule("RESULT")
    print(f"{len(artifacts)} promoted fast paths across {len(hot)} profiled call sites.")
    for a in artifacts:
        pm = a["projected_monthly"]
        print(f"  {a['call_site']:<18} {a['strategy']:<15} "
              f"covers {a['evidence']['coverage']:.0%}  "
              f"${pm['gross_saving_usd']:>8.2f}/mo saved  "
              f"(${pm['residual_model_spend_usd']:.2f} still on {a['model_replaced']})")
    print(f"\nprojected monthly saving across promoted paths: ${total_saving:.2f}")
    print(f"residual model spend on those same call sites:   ${residual:.2f}")
    print("Rejections are the point: a LOOSE call site promoted by mistake costs more "
          "trust than\nten missed savings, so the promotion rule requires beating the "
          "model's own consistency.")

    with open(os.path.join(OUT, "artifacts.json"), "w") as fh:
        json.dump(artifacts, fh, indent=2)
        fh.write("\n")
    for a in artifacts:
        path = os.path.join(OUT, f"fastpath_{a['call_site'].replace('.', '_')}.py")
        with open(path, "w") as fh:
            fh.write(f'"""Generated fast path for call site `{a["call_site"]}`.\n\n'
                     f'{a["rationale"]}\n\n'
                     f'Evidence: {json.dumps(a["evidence"])}\n'
                     f'Fallback: {a["fallback"]["action"]} ({a["fallback"]["when"]}).\n'
                     f'"""\n\nimport re\n\n\n')
            fh.write(a["script"] + "\n\n")
            fh.write(a["guard"] + "\n")
    print(f"\nwrote out/artifacts.json and {len(artifacts)} fastpath_*.py files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
