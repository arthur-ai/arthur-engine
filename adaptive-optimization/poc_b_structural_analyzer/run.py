#!/usr/bin/env python3
"""POC B end to end: structural findings from single traces, scored per pattern."""

import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from _common import spanmodel as sm   # noqa: E402
import dataflow as df                  # noqa: E402

OUT = os.path.join(HERE, "out")
BAR = "=" * 96


def main() -> int:
    traces = sm.load_corpus(os.path.join(OUT, "traces.json"))
    meta = json.load(open(os.path.join(OUT, "traces.meta.json")))
    truth = meta["ground_truth"]

    print(f"\n{BAR}\nSTRUCTURAL ANALYSIS — {len(traces)} traces, one at a time, "
          f"no corpus statistics\n{BAR}")

    all_findings: list[df.Finding] = []
    per_trace: dict[str, set[str]] = defaultdict(set)
    for trace in traces:
        for f in df.analyze(trace):
            all_findings.append(f)
            per_trace[trace["trace_id"]].add(f.pattern)

    # ── per-pattern precision / recall ───────────────────────────────────────
    print(f"\n{'pattern':<22}{'planted':>9}{'detected':>10}{'TP':>6}{'FP':>6}"
          f"{'FN':>6}{'precision':>11}{'recall':>9}{'class':>11}")
    print("-" * 96)
    classes = {p: cls for p, cls in (
        ("dead_llm_call", "PROVABLE"), ("redundant_call", "PROVABLE"),
        ("verbatim_dispatch", "LOCAL"), ("passthrough_reformat", "LOCAL"),
        ("rebuilt_prefix", "ADVISORY"))}
    totals = Counter()
    for pattern in meta["patterns"]:
        planted = {tid for tid, pats in truth.items() if pattern in pats}
        detected = {tid for tid, pats in per_trace.items() if pattern in pats}
        tp, fp, fn = len(planted & detected), len(detected - planted), len(planted - detected)
        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 1.0
        totals["tp"] += tp
        totals["fp"] += fp
        totals["fn"] += fn
        print(f"{pattern:<22}{len(planted):>9}{len(detected):>10}{tp:>6}{fp:>6}{fn:>6}"
              f"{prec:>11.3f}{rec:>9.3f}{classes[pattern]:>11}")
    prec = totals["tp"] / (totals["tp"] + totals["fp"]) if totals["tp"] + totals["fp"] else 1.0
    rec = totals["tp"] / (totals["tp"] + totals["fn"]) if totals["tp"] + totals["fn"] else 1.0
    print("-" * 96)
    print(f"{'overall':<22}{'':>9}{'':>10}{totals['tp']:>6}{totals['fp']:>6}"
          f"{totals['fn']:>6}{prec:>11.3f}{rec:>9.3f}")

    clean = {tid for tid, pats in truth.items() if not pats}
    dirty_clean = {tid for tid in clean if per_trace.get(tid)}
    print(f"\nclean controls: {len(clean)}, of which {len(dirty_clean)} produced a "
          f"false finding ({100 * len(dirty_clean) / len(clean):.1f}%)")
    for tid in list(dirty_clean)[:3]:
        print(f"   {tid[:12]} -> {sorted(per_trace[tid])}")

    # ── what the findings are worth ──────────────────────────────────────────
    print(f"\n{BAR}\nVALUE, GROUPED BY HOW MUCH EVIDENCE IT NEEDS BEFORE ACTING\n{BAR}")
    by_class: dict[str, list[df.Finding]] = defaultdict(list)
    for f in all_findings:
        by_class[f.confidence].append(f)
    order = ["PROVABLE", "LOCAL", "ADVISORY"]
    day_usd = sum(sm.cost_usd(s) for t in traces for s in t["spans"]
                  if sm.span_kind(s) == "LLM")
    print(f"corpus LLM spend: ${day_usd:.2f}\n")
    for cls in order:
        fs = by_class.get(cls, [])
        if not fs:
            continue
        usd = sum(f.saving_usd for f in fs)
        ms = sum(f.saving_ms for f in fs)
        pats = Counter(f.pattern for f in fs)
        print(f"{cls:<10} {len(fs):>4} findings   ${usd:>7.3f} ({100 * usd / day_usd:>4.1f}% "
              f"of spend)   {ms / 1000:>7.1f}s latency removed")
        for pat, n in pats.most_common():
            print(f"           {pat:<22}{n:>5}")
        if cls == "PROVABLE":
            print("           ^ safe without a guard, a replay, or an eval: nothing reads "
                  "these values")
        if cls == "LOCAL":
            print("           ^ provable in-trace, but substitution needs corpus "
                  "confirmation first (POC A)")
        if cls == "ADVISORY":
            print("           ^ caching/config change; no generated code at all")
        print()

    # ── an example of each ───────────────────────────────────────────────────
    print(f"{BAR}\nONE EXAMPLE PER PATTERN\n{BAR}")
    shown = set()
    for f in all_findings:
        if f.pattern in shown:
            continue
        shown.add(f.pattern)
        print(f"\n  [{f.confidence}] {f.pattern} @ {f.call_site}  "
              f"(trace {f.trace_id[:12]}, span {f.span_id[:8]})")
        print(f"    {f.detail}")
        print(f"    evidence: {json.dumps(f.evidence)}")
        print(f"    worth: ${f.saving_usd:.5f} and {f.saving_ms:.0f}ms per occurrence")

    with open(os.path.join(OUT, "findings.json"), "w") as fh:
        json.dump([f.__dict__ for f in all_findings], fh, indent=1)
        fh.write("\n")
    print(f"\nwrote out/findings.json ({len(all_findings)} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
