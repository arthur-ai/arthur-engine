import { useEffect, useMemo, useRef, useState } from "react";

import { createTaskTourHighlightsPlugin } from "./highlights";
import { buildTourConfig } from "./tour-config";

import { createAnalyticsPlugin, createTour, createTourStatePlugin, type StepContext, type TourEngine, type TourStatePlugin } from "@/features/tour";
import { track } from "@/services/amplitude";

export const TASK_TOUR_STORAGE_KEY = "arthur:task-tour:status";

export interface UseTaskTourEngineOptions {
  taskId: string;
  /** Used by `tour-config`'s `skipWhen` predicate to auto-skip empty-state steps. */
  isEmpty?: (skipWhenEmptyKey: string, ctx: StepContext) => boolean | Promise<boolean>;
}

export interface UseTaskTourEngineResult {
  engine: TourEngine | null;
  statePlugin: TourStatePlugin;
}

/**
 * Owns the lifecycle of the task tour's engine + state plugin.
 *
 * - The state plugin is memoized once (no taskId dependency) so its
 *   subscriber list survives engine recreation (StrictMode dev re-mount,
 *   HMR, taskId changes).
 * - The engine itself is created inside `useEffect`, NOT `useMemo`: in
 *   StrictMode dev React mounts → cleanup → re-mounts a component without
 *   freshly memoizing, which would leave the cached engine destroyed but
 *   still referenced. Tying create+destroy to one effect guarantees the
 *   engine the React tree holds is always fully wired.
 * - Auto-start fires once per engine instance when the persisted status is
 *   `unseen` or `in-progress` (so reloads mid-tour reopen at the resume
 *   point rather than stranding the panel).
 */
export function useTaskTourEngine({ taskId, isEmpty }: UseTaskTourEngineOptions): UseTaskTourEngineResult {
  const statePlugin = useMemo(() => createTourStatePlugin({ storageKey: TASK_TOUR_STORAGE_KEY }), []);
  const highlightsPlugin = useMemo(() => createTaskTourHighlightsPlugin(), []);
  const isEmptyRef = useRef(isEmpty);
  isEmptyRef.current = isEmpty;

  const [engine, setEngine] = useState<TourEngine | null>(null);
  const autoStartedRef = useRef(false);

  useEffect(() => {
    const config = buildTourConfig(taskId, {
      isEmpty: (key, ctx) => isEmptyRef.current?.(key, ctx) ?? false,
    });
    const created = createTour({
      config,
      plugins: [createAnalyticsPlugin({ track, prefix: "task-tour" }), statePlugin, highlightsPlugin],
    });
    setEngine(created);
    return () => {
      autoStartedRef.current = false;
      created.destroy();
      setEngine(null);
    };
  }, [highlightsPlugin, statePlugin, taskId]);

  useEffect(() => {
    if (!engine || autoStartedRef.current) return;
    const snapshot = statePlugin.getSnapshot();
    if (snapshot.status !== "unseen" && snapshot.status !== "in-progress") return;
    if (engine.getState().status !== "idle") return;
    autoStartedRef.current = true;
    if (snapshot.status === "in-progress") {
      const resume = statePlugin.resumePosition(engine.config);
      engine.start({ position: resume ?? undefined, resume: true });
    } else {
      engine.start();
    }
  }, [engine, statePlugin]);

  return { engine, statePlugin };
}
