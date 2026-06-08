import { describe, expect, it, vi } from "vitest";

import { createTourBus } from "../../core/events";
import type { StepCompletedEvent, TourConfig } from "../../core/types";
import { createTourStatePlugin, type PersistenceStorage } from "../createTourStatePlugin";

function memoryStorage(initial: Record<string, string> = {}): PersistenceStorage & { data: Record<string, string> } {
  const data = { ...initial };
  return {
    data,
    getItem: (key) => data[key] ?? null,
    setItem: (key, value) => {
      data[key] = value;
    },
    removeItem: (key) => {
      delete data[key];
    },
  };
}

const config: TourConfig = {
  id: "tour",
  sections: [
    {
      id: "alpha",
      steps: [
        { id: "one", target: { kind: "element", resolve: () => document.body }, content: "One" },
        { id: "two", target: { kind: "element", resolve: () => document.body }, content: "Two" },
      ],
    },
    {
      id: "intro-only",
      introduction: { title: "Intro" },
      steps: [],
    },
  ],
};

describe("createTourStatePlugin", () => {
  it("falls back to an unseen snapshot when storage is corrupted", () => {
    const plugin = createTourStatePlugin({
      storageKey: "tour",
      storage: memoryStorage({ tour: "{not-json" }),
    });

    expect(plugin.getSnapshot()).toEqual({ status: "unseen", completed: new Set() });
  });

  it("keeps in-memory state when storage writes fail", () => {
    const storage: PersistenceStorage = {
      getItem: () => null,
      setItem: () => {
        throw new Error("quota exceeded");
      },
      removeItem: () => {},
    };
    const plugin = createTourStatePlugin({ storageKey: "tour", storage });

    plugin.markCompleted("alpha.one");

    expect(plugin.getSnapshot().completed.has("alpha.one")).toBe(true);
  });

  it("uses custom completion semantics when computing resume position", () => {
    const plugin = createTourStatePlugin({
      storageKey: "tour",
      storage: memoryStorage({
        tour: JSON.stringify({ status: "in-progress", completed: ["complete:alpha:one"] }),
      }),
      getKey: (event: StepCompletedEvent) => `complete:${event.sectionId}:${event.stepId}`,
      isStepComplete: (section, step, completed) => completed.has(`complete:${section.id}:${step.id}`),
    });

    expect(plugin.resumePosition(config)).toEqual({ sectionId: "alpha", stepId: "two" });
  });

  it("uses getKey-only custom completion keys when computing resume position", () => {
    const plugin = createTourStatePlugin({
      storageKey: "tour",
      storage: memoryStorage({
        tour: JSON.stringify({ status: "in-progress", completed: ["complete:alpha:one"] }),
      }),
      getKey: (event: StepCompletedEvent) => `complete:${event.sectionId}:${event.stepId}`,
    });

    expect(plugin.resumePosition(config)).toEqual({ sectionId: "alpha", stepId: "two" });
  });

  it("records skipped tours as skipped instead of dismissed", () => {
    const plugin = createTourStatePlugin({ storageKey: "tour", storage: memoryStorage() });
    const bus = createTourBus();
    const cleanup = plugin.install({
      tourId: "tour",
      bus,
      store: {} as never,
      registerTrigger: () => {},
      registerHighlight: () => {},
      registerPreparation: () => {},
      registerLayer: () => {},
      registerQueryHook: () => {},
      registerOccluder: () => {},
      use: () => {},
    });

    bus.emit("tour:end", { tourId: "tour", reason: "skipped" });

    expect(plugin.getSnapshot().status).toBe("skipped");
    cleanup?.();
  });

  it("marks intro-only sections complete and skips them on resume", () => {
    const plugin = createTourStatePlugin({ storageKey: "tour", storage: memoryStorage() });
    plugin.markCompleted("alpha.one");
    plugin.markCompleted("alpha.two");
    plugin.markCompleted("intro-only.__intro");

    expect(plugin.resumePosition(config)).toBeNull();
  });

  it("merges cross-tab storage events into the plugin store", () => {
    const plugin = createTourStatePlugin({ storageKey: "tour", storage: memoryStorage() });
    const bus = createTourBus();
    const cleanup = plugin.install({
      tourId: "tour",
      bus,
      store: {} as never,
      registerTrigger: () => {},
      registerHighlight: () => {},
      registerPreparation: () => {},
      registerLayer: () => {},
      registerQueryHook: () => {},
      registerOccluder: () => {},
      use: () => {},
    });

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "tour",
        newValue: JSON.stringify({ status: "completed", completed: ["alpha.one", "alpha.two"] }),
      })
    );

    expect(plugin.getSnapshot().status).toBe("completed");
    expect(plugin.getSnapshot().completed.has("alpha.two")).toBe(true);
    cleanup?.();
  });

  it("resets to unseen and clears completed progress", () => {
    const storage = memoryStorage();
    const plugin = createTourStatePlugin({ storageKey: "tour", storage });
    plugin.markCompleted("alpha.one");
    plugin.setSnapshot({ status: "completed" });

    plugin.reset();

    expect(plugin.getSnapshot()).toEqual({ status: "unseen", completed: new Set() });
    expect(JSON.parse(storage.data.tour)).toEqual({ status: "unseen", completed: [] });
  });

  it("resets dismissed snapshots with custom completion keys", () => {
    const storage = memoryStorage();
    const plugin = createTourStatePlugin({
      storageKey: "tour",
      storage,
      getKey: (event: StepCompletedEvent) => `complete:${event.sectionId}:${event.stepId}`,
    });
    plugin.setSnapshot({ status: "dismissed", position: { sectionId: "alpha", stepId: "two" } });
    plugin.markCompleted("complete:alpha:one");

    plugin.reset();

    expect(plugin.getSnapshot()).toEqual({ status: "unseen", completed: new Set() });
    expect(JSON.parse(storage.data.tour)).toEqual({ status: "unseen", completed: [] });
  });

  it("ignores storage events for other persistence keys", () => {
    const plugin = createTourStatePlugin({ storageKey: "tour", storage: memoryStorage() });
    const bus = createTourBus();
    const cleanup = plugin.install({
      tourId: "tour",
      bus,
      store: {} as never,
      registerTrigger: () => {},
      registerHighlight: () => {},
      registerPreparation: () => {},
      registerLayer: () => {},
      registerQueryHook: () => {},
      registerOccluder: () => {},
      use: () => {},
    });
    plugin.markCompleted("alpha.one");

    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "other-tour",
        newValue: JSON.stringify({ status: "completed", completed: ["alpha.one", "alpha.two"] }),
      })
    );

    expect(plugin.getSnapshot().status).toBe("unseen");
    expect(plugin.getSnapshot().completed).toEqual(new Set(["alpha.one"]));
    cleanup?.();
  });

  it("does not write duplicate snapshots", () => {
    const storage = memoryStorage({ tour: JSON.stringify({ status: "unseen", completed: [] }) });
    const setItem = vi.spyOn(storage, "setItem");
    const plugin = createTourStatePlugin({ storageKey: "tour", storage });

    plugin.setSnapshot({ status: "unseen" });

    expect(setItem).not.toHaveBeenCalled();
  });
});
