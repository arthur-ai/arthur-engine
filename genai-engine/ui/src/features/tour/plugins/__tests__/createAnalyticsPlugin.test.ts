import { afterEach, describe, expect, it, vi } from "vitest";

import { createTourBus } from "../../core/events";
import type { StepContext, TourBus } from "../../core/types";
import { createAnalyticsPlugin, type CreateAnalyticsPluginOptions } from "../createAnalyticsPlugin";

const index = { sectionIndex: 0, stepIndex: 0, globalStepIndex: 0, totalSteps: 2 };
const ctx: StepContext = { tourId: "tour", sectionId: "alpha", stepId: "one", index };

/** Install the plugin against a fresh bus, returning the bus + the track spy. */
function setup(opts: Partial<CreateAnalyticsPluginOptions> = {}) {
  const track = vi.fn();
  const bus: TourBus = createTourBus();
  const plugin = createAnalyticsPlugin({ track, prefix: "task-tour", ...opts });
  const cleanup = plugin.install({
    tourId: "tour",
    bus,
    store: {} as never,
    registerTrigger: () => {},
    registerHighlight: () => {},
    registerPreparation: () => {},
    registerLayer: () => {},
    registerQueryHook: () => {},
    use: () => {},
  });
  return { track, bus, cleanup };
}

describe("createAnalyticsPlugin", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("forwards events under the configured prefix", () => {
    const { track, bus } = setup();

    bus.emit("tour:start", { tourId: "tour" });

    expect(track).toHaveBeenCalledWith("task-tour.tour:start", { tourId: "tour" });
  });

  it("appends duration_seconds to both step:completed and step:left", () => {
    let now = 0;
    vi.spyOn(performance, "now").mockImplementation(() => now);
    const { track, bus } = setup();

    now = 1000;
    bus.emit("step:enter", { ...ctx, rect: null });

    now = 3500;
    bus.emit("step:completed", { ...ctx, cause: "next" });
    bus.emit("step:left", { ...ctx, cause: "next" });

    expect(track).toHaveBeenCalledWith("task-tour.step:completed", { ...ctx, cause: "next", duration_seconds: 2.5 });
    expect(track).toHaveBeenCalledWith("task-tour.step:left", { ...ctx, cause: "next", duration_seconds: 2.5 });
  });

  it("times re-entered steps from their latest step:enter", () => {
    let now = 0;
    vi.spyOn(performance, "now").mockImplementation(() => now);
    const { track, bus } = setup();

    now = 1000;
    bus.emit("step:enter", { ...ctx, rect: null });
    now = 2000;
    bus.emit("step:enter", { ...ctx, rect: null }); // re-entry overwrites the stamp
    now = 2600;
    bus.emit("step:completed", { ...ctx, cause: "next" });

    expect(track).toHaveBeenCalledWith("task-tour.step:completed", { ...ctx, cause: "next", duration_seconds: 0.6 });
  });

  it("forwards an exit with no preceding enter (e.g. auto-skip) without a duration", () => {
    const { track, bus } = setup();

    bus.emit("step:left", { ...ctx, cause: "auto-skip" });

    expect(track).toHaveBeenCalledTimes(1);
    const [, props] = track.mock.calls[0];
    expect(props).not.toHaveProperty("duration_seconds");
  });

  it("still records the enter stamp when step:enter is filtered out of forwarding", () => {
    let now = 0;
    vi.spyOn(performance, "now").mockImplementation(() => now);
    const { track, bus } = setup({ include: ["step:completed"] });

    now = 1000;
    bus.emit("step:enter", { ...ctx, rect: null }); // not forwarded, but stamped
    now = 2000;
    bus.emit("step:completed", { ...ctx, cause: "next" });
    bus.emit("step:left", { ...ctx, cause: "next" }); // not forwarded

    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith("task-tour.step:completed", { ...ctx, cause: "next", duration_seconds: 1 });
  });
});
