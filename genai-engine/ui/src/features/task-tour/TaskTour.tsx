import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CertificateDialog } from "./components/CertificateDialog";
import { ChecklistTour } from "./components/ChecklistTour";
import { ResumeFab } from "./components/ResumeFab";
import { createTaskTourHighlightsPlugin } from "./highlights";
import { buildTourConfig, isStubStep } from "./tour-config";

import {
  createAnalyticsPlugin,
  createChecklistProgressPlugin,
  createPersistencePlugin,
  createTour,
  TourProvider,
  useReactRouterNavigator,
  useTourPersistence,
  type ChecklistProgress,
  type StepAdvanceEvent,
  type TourConfig,
  type TourEngine,
} from "@/features/tour";
import { track } from "@/services/amplitude";

export const TASK_TOUR_STORAGE_KEY = "arthur:task-tour:status";
const TASK_TOUR_PROGRESS_STORAGE_KEY = "arthur:task-tour:progress";

/**
 * Builds the progress-set key for a given (sectionId, stepId) pair. Stub
 * sections collapse to a single `${sectionId}.__intro` marker so the
 * placeholder step ID never leaks into the storage key.
 */
const taskTourStepKey = (sectionId: string, stepId: string): string => (isStubStep(stepId) ? `${sectionId}.__intro` : `${sectionId}.${stepId}`);

/**
 * Maps a `step:advance` event to the same key shape, used by the
 * `createChecklistProgressPlugin`'s `getKey` option to record progress.
 */
const taskTourProgressKey = (event: StepAdvanceEvent): string => taskTourStepKey(event.sectionId, event.stepId);

/**
 * Walks the tour config and returns the first step the user has not yet
 * completed (according to `progress`), so a resume can land on the next
 * outstanding step rather than restart from the top. Returns `null` when
 * every step is recorded as complete.
 */
function findResumePosition(config: TourConfig, progress: ChecklistProgress): { sectionId: string; stepId: string } | null {
  for (const section of config.sections) {
    for (const step of section.steps) {
      if (!progress.has(taskTourStepKey(section.id, step.id))) {
        return { sectionId: section.id, stepId: step.id };
      }
    }
  }
  return null;
}

export interface TaskTourProps {
  /** Required: the task the tour should bind its routes against. */
  taskId: string;
  /** Optional human-readable name displayed on the completion certificate. */
  workspaceLabel?: string;
}

/**
 * Top-level mount for the Evals 101 / ADLC tour. Owns the engine lifecycle,
 * binds it to React Router via `useReactRouterNavigator`, and drives the
 * persistence-aware auto-show / resume / hide behaviour:
 *
 * - `unseen`        → auto-start once on first mount; user sees Section 1 intro
 * - `in-progress`   → auto-resume on mount (engine starts at the first
 *                     incomplete step from `progressPlugin`, so a reload or
 *                     intra-app re-mount mid-tour reopens where the user
 *                     left off rather than stranding the panel
 * - `dismissed`     → render only the floating `ResumeFab` (which also
 *                     resumes at the first incomplete step on click)
 * - `completed`     → render nothing (and unmount the FAB)
 *
 * Persistence is owned by the engine plugin: the plugin writes to
 * localStorage on every relevant bus event (`tour:start`, `tour:resume`,
 * `tour:dismiss`, `tour:end`) and exposes a reactive `subscribe()` API that
 * `useTourPersistence(plugin)` plugs into. This component never writes
 * persistence directly — every status change flows through the engine's
 * actions.
 *
 * Engine creation lives in `useEffect`, NOT `useMemo`. This is deliberate: in
 * React StrictMode dev the `useMemo + useEffect-cleanup` pattern leaves the
 * cached engine destroyed but still referenced — the cleanup uninstalls the
 * persistence plugin (clears bus handlers) while the same engine instance is
 * reused on the re-mount. Subsequent `actions.dismiss()` calls would then
 * mutate engine state but `bus.emit("tour:dismiss")` would hit an empty bus,
 * so the persistence status would never flip to `"dismissed"` and the resume
 * FAB would never appear. Tying creation+destruction to a single `useEffect`
 * pair guarantees each cleanup is followed by a fresh `createTour`, so the
 * engine the React tree holds is always fully wired.
 *
 * The persistence plugin is still memoized once (no taskId dependency) so its
 * subscriber list and in-memory `current` survive engine recreation.
 */
export function TaskTour({ taskId, workspaceLabel }: TaskTourProps) {
  const navigator = useReactRouterNavigator();

  const persistencePlugin = useMemo(() => createPersistencePlugin({ storageKey: TASK_TOUR_STORAGE_KEY }), []);
  const progressPlugin = useMemo(
    () =>
      createChecklistProgressPlugin({
        storageKey: TASK_TOUR_PROGRESS_STORAGE_KEY,
        getKey: taskTourProgressKey,
      }),
    []
  );
  const highlightsPlugin = useMemo(() => createTaskTourHighlightsPlugin(), []);

  const [engine, setEngine] = useState<TourEngine | null>(null);

  useEffect(() => {
    const created = createTour({
      config: buildTourConfig(taskId),
      plugins: [createAnalyticsPlugin({ track, prefix: "task-tour" }), persistencePlugin, progressPlugin, highlightsPlugin],
    });
    setEngine(created);
    return () => {
      created.destroy();
    };
  }, [highlightsPlugin, persistencePlugin, progressPlugin, taskId]);

  const status = useTourPersistence(persistencePlugin);

  // Auto-start once per mount when the tour is owed to the user. `unseen`
  // means they've never seen it; `in-progress` means they started but the
  // engine was torn down (page reload, intra-app navigation that unmounted
  // `TaskLayout`, taskId change), and we want the panel to reappear at the
  // next outstanding step rather than leave persistence stranded with no
  // visible tour. We use a ref to gate so the side-effect doesn't re-fire
  // when `status` flickers — e.g. the persistence plugin writes
  // `in-progress` synchronously inside `start()`, which re-renders with a
  // new status before this effect has settled.
  const autoStartedRef = useRef(false);
  useEffect(() => {
    if (autoStartedRef.current) return;
    if (!engine) return;
    if (status !== "unseen" && status !== "in-progress") return;
    if (engine.getState().status !== "idle") return;
    autoStartedRef.current = true;
    if (status === "in-progress") {
      const resumePosition = findResumePosition(engine.config, progressPlugin.getProgress());
      engine.start(resumePosition ?? undefined);
    } else {
      engine.start();
    }
  }, [engine, progressPlugin, status]);

  const [certificateOpen, setCertificateOpen] = useState(false);

  // The plugin already writes `"completed"` on `tour:end{completed}`; this
  // handler only owns the certificate-dialog UI side-effect.
  const handleComplete = useCallback(() => {
    setCertificateOpen(true);
  }, []);

  const handleResume = useCallback(() => {
    if (!engine) return;
    // The plugin writes `"in-progress"` on both `tour:start` and `tour:resume`,
    // so we just dispatch the right engine action for the current state.
    const engineState = engine.getState();
    if (engineState.status === "paused") {
      engine.resume();
      return;
    }
    // Idle (fresh page load after dismissal) or terminal (completed/skipped
    // re-run) — `start()` resets the engine cleanly. When resuming a
    // dismissed tour we honour the persisted progress so the user lands on
    // the next outstanding step, not back at section 0.
    const resumePosition = findResumePosition(engine.config, progressPlugin.getProgress());
    engine.start(resumePosition ?? undefined);
  }, [engine, progressPlugin]);

  const handleCertificateClose = useCallback(() => {
    setCertificateOpen(false);
  }, []);

  // `completed` state with the certificate already closed → render nothing.
  if (status === "completed" && !certificateOpen) {
    return null;
  }

  const checklistEnabled = status === "unseen" || status === "in-progress";

  return (
    <>
      {engine ? (
        <TourProvider tour={engine} navigator={navigator}>
          <ChecklistTour enabled={checklistEnabled} progressPlugin={progressPlugin} onComplete={handleComplete} />
        </TourProvider>
      ) : null}
      {/* Dismissed state: render the resume FAB independently of the engine's
          internal status, because the dismissed status may persist across page
          reloads when the engine is freshly created in the `idle` state. Gated
          on `engine` so the first paint before the creation `useEffect` commits
          doesn't expose a button whose click would no-op. */}
      {engine && !checklistEnabled && !certificateOpen ? <ResumeFab onClick={handleResume} /> : null}

      <CertificateDialog open={certificateOpen} workspaceLabel={workspaceLabel} onClose={handleCertificateClose} />
    </>
  );
}
