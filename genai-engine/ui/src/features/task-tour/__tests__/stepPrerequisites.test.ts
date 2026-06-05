import { describe, expect, it } from "vitest";

import { buildTourConfig } from "../tour-config";

/**
 * Route-less, prep-less steps that are intentionally so: their target lives in
 * the always-present app shell (the sidebar), so they're reachable out of order
 * (checklist jump / resume) with no setup. Every other step establishes its
 * context with a static `route` or a `prepareKey`.
 *
 * Adding a step without a `route` or `prepareKey` fails this test until it's
 * classified here — turning "did we remember the prerequisite?" from tribal
 * knowledge into an enforced contract.
 *
 * (The former "linear-only" category — the prompt-playground beats that
 * depended on ephemeral state — was retired once `playgroundOpened` made them
 * jump-safe via the URL-prompt data source.)
 */
const ROUTELESS_REVIEWED: Record<string, "shell"> = {
  "evals.open-evaluate": "shell",
  "traces.open-observe": "shell",
  "datasets.open-datasets": "shell",
  "datasets.open-traces-for-dataset": "shell",
  "prompts.open-prompts": "shell",
  "deploy.verify-eval-passes": "shell",
};

describe("task tour step prerequisites", () => {
  const config = buildTourConfig("task-under-test");
  const steps = config.sections.flatMap((section) => section.steps.map((step) => ({ key: `${section.id}.${step.id}`, step })));

  it("every step can establish its context on out-of-order entry (route | prepareKey | reviewed route-less)", () => {
    const unaccounted = steps.filter(({ key, step }) => !step.route && !step.prepare && !(key in ROUTELESS_REVIEWED)).map(({ key }) => key);
    expect(unaccounted, `route-less steps missing a prepareKey or a ROUTELESS_REVIEWED entry: ${unaccounted.join(", ")}`).toEqual([]);
  });

  it("the route-less allowlist has no stale entries", () => {
    const stale = Object.keys(ROUTELESS_REVIEWED).filter((key) => {
      const entry = steps.find((s) => s.key === key);
      return !entry || Boolean(entry.step.route) || Boolean(entry.step.prepare);
    });
    expect(stale, `stale ROUTELESS_REVIEWED entries (now have a route/prepareKey, or no longer exist): ${stale.join(", ")}`).toEqual([]);
  });
});
