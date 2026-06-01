import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createTourEngine } from "../engine";
import type { StepCompletedEvent, StepLeftEvent, TourConfig, TourNavigator } from "../types";

const elementTarget = (element: Element | null = document.body) => ({
  kind: "element" as const,
  resolve: () => element,
});

function step(id: string, overrides: Partial<TourConfig["sections"][number]["steps"][number]> = {}) {
  return {
    id,
    target: elementTarget(),
    content: id,
    ...overrides,
  };
}

const twoStepConfig = (overrides: Partial<TourConfig> = {}): TourConfig => ({
  id: "tour",
  sections: [
    {
      id: "section-a",
      steps: [step("one"), step("two")],
    },
    {
      id: "section-b",
      steps: [step("three")],
    },
  ],
  ...overrides,
});

describe("createTourEngine actions", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns promises from public transition actions", async () => {
    const engine = createTourEngine({ config: twoStepConfig() });

    await expect(engine.start()).resolves.toBeUndefined();
    await expect(engine.next()).resolves.toBeUndefined();
    await expect(engine.prev()).resolves.toBeUndefined();
    await expect(engine.goTo({ sectionId: "section-b", stepId: "three" })).resolves.toBeUndefined();
    await expect(engine.skipSection()).resolves.toBeUndefined();

    const skipEngine = createTourEngine({ config: twoStepConfig() });
    await skipEngine.start();
    await expect(skipEngine.skip()).resolves.toBeUndefined();

    const resumeEngine = createTourEngine({ config: twoStepConfig() });
    await resumeEngine.start();
    await resumeEngine.dismiss();
    await expect(resumeEngine.resume()).resolves.toBeUndefined();

    const introEngine = createTourEngine({
      config: {
        id: "intro-tour",
        sections: [{ id: "intro", introduction: { title: "Intro" }, steps: [] }],
      },
    });
    await introEngine.start();
    await expect(introEngine.acknowledgeIntroduction()).resolves.toBeUndefined();
  });

  it("completes safely when started with an empty config", async () => {
    const engine = createTourEngine({ config: { id: "empty", sections: [] } });

    await engine.start();

    expect(engine.getState()).toEqual({ status: "completed" });
  });

  it("uses resumePosition when start is asked to resume", async () => {
    const engine = createTourEngine({
      config: twoStepConfig(),
      resumePosition: () => ({ sectionId: "section-b", stepId: "three" }),
    });

    await engine.start({ resume: true });

    expect(engine.getState()).toMatchObject({
      status: "step",
      sectionId: "section-b",
      stepId: "three",
    });
  });

  it("advances intro-only sections and records their intro marker through lifecycle events", async () => {
    const introAck = vi.fn();
    const engine = createTourEngine({
      config: {
        id: "intro-tour",
        sections: [
          { id: "welcome", introduction: { title: "Welcome" }, steps: [] },
          { id: "next", steps: [step("first")] },
        ],
      },
    });
    engine.on("section:intro:acknowledge", introAck);

    await engine.start();
    await engine.acknowledgeIntroduction();

    expect(introAck).toHaveBeenCalledWith({ tourId: "intro-tour", sectionId: "welcome" });
    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "next", stepId: "first" });
  });

  it("pauses at section boundaries when configured", async () => {
    const engine = createTourEngine({
      config: twoStepConfig({ sectionCompletion: "pause" }),
    });

    await engine.start();
    await engine.next();
    await engine.next();

    expect(engine.getState()).toMatchObject({
      status: "sectionComplete",
      sectionId: "section-a",
      sectionIndex: 0,
      nextSectionId: "section-b",
      nextSectionIndex: 1,
    });
  });

  it("continues from a paused section boundary to the next section", async () => {
    const engine = createTourEngine({
      config: twoStepConfig({ sectionCompletion: "pause" }),
    });

    await engine.start();
    await engine.next();
    await engine.next();
    await engine.continueFromSectionComplete();

    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-b", stepId: "three" });
  });

  it("preserves default auto-advance behavior at section boundaries", async () => {
    const engine = createTourEngine({ config: twoStepConfig() });

    await engine.start();
    await engine.next();
    await engine.next();

    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-b", stepId: "three" });
  });

  it("emits one step:left event when skipWhen auto-advances", async () => {
    const left: StepLeftEvent[] = [];
    const engine = createTourEngine({
      config: {
        id: "skip-tour",
        sections: [
          {
            id: "main",
            steps: [step("skip-me", { skipWhen: () => true }), step("after")],
          },
        ],
      },
    });
    engine.on("step:left", (event) => left.push(event));

    await engine.start();

    expect(left).toHaveLength(1);
    expect(left[0]).toMatchObject({ stepId: "skip-me", cause: "auto-skip" });
    expect(engine.getState()).toMatchObject({ status: "step", stepId: "after" });
  });

  it("emits step:completed for forward progress only", async () => {
    const completed: StepCompletedEvent[] = [];
    const engine = createTourEngine({ config: twoStepConfig() });
    engine.on("step:completed", (event) => completed.push(event));

    await engine.start();
    await engine.goTo({ sectionId: "section-b", stepId: "three" });
    await engine.prev();
    await engine.next();

    expect(completed.map((event) => [event.stepId, event.cause])).toEqual([
      ["one", "goTo-forward"],
      ["two", "next"],
    ]);
  });

  it("coalesces concurrent next calls from the same step", async () => {
    const completed: StepCompletedEvent[] = [];
    const left: StepLeftEvent[] = [];
    const engine = createTourEngine({ config: twoStepConfig() });
    engine.on("step:completed", (event) => completed.push(event));
    engine.on("step:left", (event) => left.push(event));

    await engine.start();
    await Promise.all([engine.next(), engine.next()]);

    expect(completed.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(left.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-a", stepId: "two" });
  });

  it("coalesces overlapping goTo calls from the same step", async () => {
    const completed: StepCompletedEvent[] = [];
    const left: StepLeftEvent[] = [];
    const engine = createTourEngine({ config: twoStepConfig() });
    engine.on("step:completed", (event) => completed.push(event));
    engine.on("step:left", (event) => left.push(event));

    await engine.start();
    await Promise.all([engine.goTo({ sectionId: "section-b", stepId: "three" }), engine.goTo({ sectionId: "section-b", stepId: "three" })]);

    expect(completed.map((event) => [event.stepId, event.cause])).toEqual([["one", "goTo-forward"]]);
    expect(left.map((event) => [event.stepId, event.cause])).toEqual([["one", "goTo-forward"]]);
    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-b", stepId: "three" });
  });

  it("allows next after goTo re-enters the active step", async () => {
    const completed: StepCompletedEvent[] = [];
    const left: StepLeftEvent[] = [];
    const engine = createTourEngine({ config: twoStepConfig() });
    engine.on("step:completed", (event) => completed.push(event));
    engine.on("step:left", (event) => left.push(event));

    await engine.start();
    await engine.goTo({ sectionId: "section-a", stepId: "one" });
    await engine.next();

    expect(completed.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(left.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-a", stepId: "two" });
  });

  it("allows next after start targets the active step", async () => {
    const completed: StepCompletedEvent[] = [];
    const left: StepLeftEvent[] = [];
    const engine = createTourEngine({ config: twoStepConfig() });
    engine.on("step:completed", (event) => completed.push(event));
    engine.on("step:left", (event) => left.push(event));

    await engine.start();
    await engine.start({ position: { sectionId: "section-a", stepId: "one" } });
    await engine.next();

    expect(completed.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(left.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-a", stepId: "two" });
  });

  it("treats goTo for the active section as a no-op", async () => {
    const completed: StepCompletedEvent[] = [];
    const left: StepLeftEvent[] = [];
    const engine = createTourEngine({ config: twoStepConfig() });
    engine.on("step:completed", (event) => completed.push(event));
    engine.on("step:left", (event) => left.push(event));

    await engine.start();
    await engine.goTo({ sectionId: "section-a" });

    expect(completed).toEqual([]);
    expect(left).toEqual([]);
    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-a", stepId: "one" });

    await engine.next();

    expect(completed.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(left.map((event) => [event.stepId, event.cause])).toEqual([["one", "next"]]);
    expect(engine.getState()).toMatchObject({ status: "step", sectionId: "section-a", stepId: "two" });
  });

  it("navigates routes before resolving step targets", async () => {
    const targetResolver = vi.fn(() => document.querySelector("[data-tour-target]"));
    let location = { pathname: "/start", search: "", hash: "" };
    const navigator: TourNavigator = {
      getLocation: () => location,
      navigate: async (to) => {
        location = { pathname: to, search: "", hash: "" };
        const target = document.createElement("button");
        target.dataset.tourTarget = "ready";
        document.body.appendChild(target);
      },
    };
    const engine = createTourEngine({
      config: {
        id: "route-tour",
        sections: [
          {
            id: "route-section",
            steps: [
              step("routed", {
                route: "/destination",
                target: { kind: "element", resolve: targetResolver },
              }),
            ],
          },
        ],
      },
      navigator,
    });

    await engine.start();

    expect(targetResolver).toHaveReturnedWith(document.querySelector("[data-tour-target]"));
    expect(engine.getState()).toMatchObject({ status: "step", stepId: "routed" });
  });

  it("does not resolve routed targets when navigation lands on the wrong destination", async () => {
    const targetResolver = vi.fn(() => document.querySelector("[data-routed-target]"));
    let location = { pathname: "/start", search: "", hash: "" };
    const navigator: TourNavigator = {
      getLocation: () => location,
      navigate: async () => {
        location = { pathname: "/wrong", search: "", hash: "" };
        const target = document.createElement("button");
        target.dataset.routedTarget = "stale";
        document.body.appendChild(target);
      },
    };
    const engine = createTourEngine({
      config: {
        id: "route-tour",
        sections: [
          {
            id: "route-section",
            steps: [
              step("routed", {
                route: "/destination",
                target: { kind: "element", resolve: targetResolver },
              }),
            ],
          },
        ],
      },
      navigator,
    });
    const found = vi.fn();
    const lost = vi.fn();
    engine.on("target:found", found);
    engine.on("target:lost", lost);

    await engine.start();

    expect(location.pathname).toBe("/wrong");
    expect(found).not.toHaveBeenCalled();
    expect(lost).toHaveBeenCalledWith({ tourId: "route-tour", sectionId: "route-section", stepId: "routed" });
  });

  it("does not resolve stale preparation requests after a newer transition starts", async () => {
    const found: string[] = [];
    const stalePreparation: {
      resolve?: (result: { ready: boolean }) => void;
    } = {};
    const engine = createTourEngine({
      config: {
        id: "prep-tour",
        sections: [
          {
            id: "main",
            steps: [
              step("slow", {
                prepare: { key: "slow-prep" },
                target: { kind: "selector", selector: "[data-slow]" },
              }),
              step("fast", {
                target: { kind: "selector", selector: "[data-fast]" },
              }),
            ],
          },
        ],
      },
    });
    engine.onPrepareRequested((request) => {
      stalePreparation.resolve = request.resolve;
    });
    engine.on("target:found", (event) => found.push(event.stepId));

    const startPromise = engine.start();
    await vi.waitFor(() => expect(stalePreparation.resolve).toBeDefined());

    const fast = document.createElement("button");
    fast.dataset.fast = "true";
    document.body.appendChild(fast);
    await engine.goTo({ sectionId: "main", stepId: "fast" });

    const slow = document.createElement("button");
    slow.dataset.slow = "true";
    document.body.appendChild(slow);
    stalePreparation.resolve?.({ ready: true });
    await startPromise;

    expect(found).toEqual(["fast"]);
    expect(engine.getState()).toMatchObject({ status: "step", stepId: "fast" });
  });

  it("settles a stale preparation transition when a newer transition aborts it", async () => {
    const stalePreparation: {
      signal?: AbortSignal;
    } = {};
    const engine = createTourEngine({
      config: {
        id: "prep-tour",
        sections: [
          {
            id: "main",
            steps: [
              step("slow", {
                prepare: { key: "slow-prep" },
                target: { kind: "selector", selector: "[data-slow]" },
              }),
              step("fast", {
                target: { kind: "selector", selector: "[data-fast]" },
              }),
            ],
          },
        ],
      },
    });
    engine.onPrepareRequested((request) => {
      stalePreparation.signal = request.signal;
    });

    const startPromise = engine.start();
    await vi.waitFor(() => expect(stalePreparation.signal).toBeDefined());

    const fast = document.createElement("button");
    fast.dataset.fast = "true";
    document.body.appendChild(fast);
    await engine.goTo({ sectionId: "main", stepId: "fast" });

    const settleState = await Promise.race([
      startPromise.then(() => "resolved" as const),
      new Promise<"pending">((resolve) => window.setTimeout(() => resolve("pending"), 0)),
    ]);

    expect(stalePreparation.signal?.aborted).toBe(true);
    expect(settleState).toBe("resolved");
  });

  it("warns when a custom trigger has no registered factory", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const engine = createTourEngine({
      config: {
        id: "custom-tour",
        sections: [
          {
            id: "main",
            steps: [step("custom", { advanceOn: { type: "custom", key: "missing" } })],
          },
        ],
      },
    });

    await engine.start();

    expect(warn).toHaveBeenCalledWith(expect.stringContaining("missing custom trigger"), expect.objectContaining({ key: "missing" }));
  });

  it("scopes action triggers to the engine that emitted the action", async () => {
    const engineA = createTourEngine({
      config: {
        id: "tour-a",
        sections: [
          {
            id: "main",
            steps: [step("a-one", { advanceOn: { type: "action", name: "finish" } }), step("a-two")],
          },
        ],
      },
    });
    const engineB = createTourEngine({
      config: {
        id: "tour-b",
        sections: [
          {
            id: "main",
            steps: [step("b-one", { advanceOn: { type: "action", name: "finish" } }), step("b-two")],
          },
        ],
      },
    });

    await Promise.all([engineA.start(), engineB.start()]);
    engineB.emitAction("finish");

    await vi.waitFor(() => expect(engineB.getState()).toMatchObject({ status: "step", stepId: "b-two" }));
    expect(engineA.getState()).toMatchObject({ status: "step", stepId: "a-one" });
  });

  it("can refresh the active target after step UI changes", async () => {
    const first = document.createElement("button");
    const second = document.createElement("section");
    let target: Element = first;
    const found: Element[] = [];
    const engine = createTourEngine({
      config: {
        id: "refresh-tour",
        sections: [
          {
            id: "main",
            steps: [
              step("dynamic", {
                target: { kind: "element", resolve: () => target },
              }),
            ],
          },
        ],
      },
    });
    engine.on("target:found", (event) => found.push(event.element));

    await engine.start();
    target = second;
    engine.refreshTarget();

    expect(found).toEqual([first, second]);
  });

  it("clears pending fallback auto-complete timers when dismissed", async () => {
    vi.useFakeTimers();
    try {
      const engine = createTourEngine({
        config: {
          id: "fallback-tour",
          sections: [
            {
              id: "main",
              steps: [
                step("missing", {
                  target: elementTarget(null),
                  fallback: { kind: "auto-complete", afterMs: 10 },
                }),
                step("after"),
              ],
            },
          ],
        },
      });

      await engine.start();
      await engine.dismiss();
      await vi.runOnlyPendingTimersAsync();

      expect(engine.getState()).toMatchObject({ status: "dismissed" });
    } finally {
      vi.useRealTimers();
    }
  });

  it("ignores transition actions after destroy", async () => {
    const engine = createTourEngine({ config: twoStepConfig() });

    await engine.start();
    engine.destroy();
    await engine.next();

    expect(engine.getState()).toMatchObject({ status: "step", stepId: "one" });
  });
});
