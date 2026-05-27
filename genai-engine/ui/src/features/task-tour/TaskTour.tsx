import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import { CertificateDialog } from "./components/CertificateDialog";
import { ChecklistTour } from "./components/ChecklistTour";
import { ResumeFab } from "./components/ResumeFab";
import { TracesTourBridge } from "./components/TracesTourBridge";
import { createTaskTourHighlightsPlugin } from "./highlights";
import { buildTourConfig, getTaskTourStepLabel, isStubStep } from "./tour-config";

import {
  createAnalyticsPlugin,
  createChecklistProgressPlugin,
  createPersistencePlugin,
  createTour,
  TourProvider,
  useChecklistProgress,
  useReactRouterNavigator,
  useTourPersistence,
  type ChecklistProgress,
  type StepAdvanceEvent,
  type TourConfig,
  type TourEngine,
  type TourState,
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

function resolveResumeFabLabel(config: TourConfig | undefined, state: TourState, progress: ChecklistProgress): string {
  if (state.status === "running" || state.status === "paused") {
    return getTaskTourStepLabel(state.sectionId, state.stepId);
  }

  if (config) {
    const resumePosition = findResumePosition(config, progress);
    if (resumePosition) {
      return getTaskTourStepLabel(resumePosition.sectionId, resumePosition.stepId);
    }
  }

  return "Resume tour";
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
  // Auto-start once per engine instance when the tour is owed to the user.
  // `unseen` means they've never seen it; `in-progress` means they started
  // but the engine was torn down (page reload, HMR, taskId change), and we
  // want the panel to reappear at the next outstanding step rather than leave
  // persistence stranded with no visible tour. We use a ref to gate so the
  // side-effect doesn't re-fire when `status` flickers — e.g. the persistence
  // plugin writes `in-progress` synchronously inside `start()`, which
  // re-renders with a new status before `goToPosition` has flipped the engine
  // out of `idle`. The ref is reset in the engine effect cleanup so Vite HMR
  // recreates can auto-resume instead of stranding the UI with no panel and
  // no resume FAB.
  const autoStartedRef = useRef(false);

  useEffect(() => {
    const created = createTour({
      config: buildTourConfig(taskId),
      plugins: [createAnalyticsPlugin({ track, prefix: "task-tour" }), persistencePlugin, progressPlugin, highlightsPlugin],
    });
    setEngine(created);
    return () => {
      autoStartedRef.current = false;
      created.destroy();
      setEngine(null);
    };
  }, [highlightsPlugin, persistencePlugin, progressPlugin, taskId]);

  const status = useTourPersistence(persistencePlugin);
  const progress = useChecklistProgress(progressPlugin);
  const idleTourState = useMemo<TourState>(() => ({ status: "idle" }), []);
  const subscribeEngine = useCallback((onStoreChange: () => void) => (engine ? engine.subscribe(onStoreChange) : () => {}), [engine]);
  const getEngineState = useCallback(() => (engine ? engine.getState() : idleTourState), [engine, idleTourState]);
  const tourState = useSyncExternalStore(subscribeEngine, getEngineState, getEngineState);
  const resumeFabLabel = useMemo(() => resolveResumeFabLabel(engine?.config, tourState, progress), [engine?.config, progress, tourState]);

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
  const [fabAnchorRect, setFabAnchorRect] = useState<DOMRect | null>(null);
  const [panelAnchoredToFab, setPanelAnchoredToFab] = useState(false);

  useEffect(() => {
    if (status === "dismissed") {
      setPanelAnchoredToFab(false);
    }
  }, [status]);

  const handleFabAnchorRectChange = useCallback((rect: DOMRect | null) => {
    setFabAnchorRect(rect);
  }, []);

  // The plugin already writes `"completed"` on `tour:end{completed}`; this
  // handler only owns the certificate-dialog UI side-effect.
  const handleComplete = useCallback(() => {
    setCertificateOpen(true);
  }, []);

  const handleResume = useCallback(() => {
    if (!engine) return;
    const engineState = engine.getState();
    if (panelAnchoredToFab && engineState.status === "running") {
      return;
    }
    setPanelAnchoredToFab(true);
    // The plugin writes `"in-progress"` on both `tour:start` and `tour:resume`,
    // so we just dispatch the right engine action for the current state.
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
  }, [engine, panelAnchoredToFab, progressPlugin]);

  const handleCertificateClose = useCallback(() => {
    setCertificateOpen(false);
  }, []);

  // `completed` state with the certificate already closed → render nothing.
  if (status === "completed" && !certificateOpen) {
    return null;
  }

  const checklistEnabled = status === "unseen" || status === "in-progress";
  const showResumeFab = Boolean(engine && !certificateOpen && (status === "dismissed" || panelAnchoredToFab));

  return (
    <>
      {engine ? (
        <TourProvider tour={engine} navigator={navigator}>
          <TracesTourBridge taskId={taskId} />
          <ChecklistTour
            enabled={checklistEnabled}
            progressPlugin={progressPlugin}
            onComplete={handleComplete}
            panelAnchorRect={panelAnchoredToFab ? fabAnchorRect : null}
          />
        </TourProvider>
      ) : null}
      {showResumeFab ? (
        <ResumeFab
          label={resumeFabLabel}
          attractAttention={status === "dismissed"}
          onClick={handleResume}
          onAnchorRectChange={handleFabAnchorRectChange}
        />
      ) : null}

      <CertificateDialog open={certificateOpen} workspaceLabel={workspaceLabel} onClose={handleCertificateClose} />
    </>
  );
}
